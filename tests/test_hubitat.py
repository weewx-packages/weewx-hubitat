import http.server
import json
import logging
import queue
import threading
import types

import configobj
import pytest
import weewx
import weewx.restx

import hubitat


class FakeHubitat:
    """A local stand-in for the Hubitat device that records what it is sent."""

    def __init__(self, status=200):
        self.posts = []
        self.status = status
        self.got_post = threading.Event()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers['Content-Length'])
                owner.posts.append((self.path, self.headers['Content-Type'],
                                    json.loads(self.rfile.read(length))))
                self.send_response(owner.status)
                self.send_header('Content-Length', '0')
                self.end_headers()
                owner.got_post.set()

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:%d' % self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.thread.join()
        self.httpd.server_close()


PACKET = {'dateTime': 1700000000, 'usUnits': weewx.US,
          'outTemp': 68.04, 'outHumidity': 55.0,
          'windSpeed': 5.0, 'windDir': 7.0, 'windGust': None,
          'barometer': 29.921, 'pressure': 29.5}


def make_thread(server_url, q=None, **options):
    return hubitat.HubitatThread(q or queue.Queue(), None, server_url=server_url,
                                 retry_wait=0, **options)


def test_packet_is_posted_as_json_with_hubitat_attribute_names():
    with FakeHubitat() as server:
        make_thread(server.url).process_record(PACKET, None)
        path, content_type, body = server.posts[0]
        assert path == '/'
        assert content_type == 'application/json'
        # The Hubitat driver reads every key as an attribute, so the values
        # are strings with the formats of _FORMATS. windGust is None and
        # pressure has no attribute, so neither is sent.
        assert body == {'temperature': '68.0', 'humidity': '55',
                        'windSpeed': '5.0', 'windDirection': '007',
                        'barometer': '29.921'}


def test_target_unit_converts_before_posting():
    with FakeHubitat() as server:
        make_thread(server.url, target_unit='metric').process_record(PACKET, None)
        body = server.posts[0][2]
        assert body['temperature'] == '20.0'
        # 29.921 inHg
        assert body['barometer'] == '1013.241'


def test_loop_packet_travels_through_the_queue():
    with FakeHubitat() as server:
        q = queue.Queue()
        thread = make_thread(server.url, q)
        thread.start()
        q.put(PACKET)
        # With max_backlog = 0 a packet is dropped when another one is already
        # waiting, so the stop signal waits for the post.
        assert server.got_post.wait(10)
        q.put(None)
        thread.join(10)
        assert not thread.is_alive()
        assert len(server.posts) == 1


def test_server_error_is_a_failed_post():
    with FakeHubitat(status=500) as server:
        with pytest.raises(weewx.restx.FailedPost):
            make_thread(server.url).process_record(PACKET, None)


def make_service(tmp_path, monkeypatch, bound=True, **options):
    monkeypatch.setattr(hubitat.HubitatThread, 'start', lambda self: None)
    bound_to = []
    engine = types.SimpleNamespace(bind=lambda *args: bound_to.append(args))
    site = {'server_url': 'http://192.0.2.1:39501'}
    site.update(options)
    config = configobj.ConfigObj({
        'WEEWX_ROOT': str(tmp_path),
        'StdRESTful': {'Hubitat': site},
        'DatabaseTypes': {'SQLite': {'driver': 'weedb.sqlite',
                                     'SQLITE_ROOT': str(tmp_path)}}})
    if bound:
        config['DataBindings'] = {'wx_binding': {'database': 'archive',
                                                 'manager': 'weewx.manager.Manager',
                                                 'table_name': 'archive'}}
        config['Databases'] = {'archive': {'database_type': 'SQLite',
                                           'database_name': 'weewx.sdb'}}
    service = hubitat.Hubitat(engine, config)
    return service, bound_to


def test_service_starts_and_binds_loop_packets(tmp_path, monkeypatch):
    service, bound_to = make_service(tmp_path, monkeypatch, post_interval='30')
    assert service.loop_thread.server_url == 'http://192.0.2.1:39501'
    assert service.loop_thread.post_interval == 30
    assert bound_to[0][0] == weewx.NEW_LOOP_PACKET


def test_service_starts_on_a_station_without_wx_binding(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch, bound=False)
    assert service.loop_thread.manager_dict is None


@pytest.mark.parametrize('options', [{'server_url': 'hubURL_from_hubitat_device'},
                                     {'server_url': 'replace_me'},
                                     {'server_url': '192.0.2.1:39501'},
                                     {'target_unit': 'kelvin'},
                                     {'enable': 'false'}])
def test_service_does_not_start_with_unusable_settings(tmp_path, monkeypatch, options):
    service, bound_to = make_service(tmp_path, monkeypatch, **options)
    assert not hasattr(service, 'loop_thread')
    assert bound_to == []
