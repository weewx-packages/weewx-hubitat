#
# Copyright (c) 2020, Denny Page
# All rights reserved.
#
# Modified 2026-10-23 by weewx-packages: Python 3 only, Python 2 and WeeWX 3
#   fallbacks removed; the uploader does not start with the placeholder or an
#   invalid server_url. See the changelog.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
This extension posts data to a Hubitat device


Configuration:

[StdRESTful]
    [[Hubitat]]
        server_url = HUBITAT_URL


    Required parameters:
        server_url: Hubitat URL

    Optional parameters:
        post_interval: Interval in seconds for posting updates to the Hubitat (default 60)

        target_unit: Unit system to use for posting to Hubitat if different than the WeeWX database (default None)

        Other standard restx options such as 'log_success' are also accepted
"""

import json
import logging
import queue

import weewx
import weewx.manager
import weewx.restx
import weewx.units

VERSION = "1.1"

log = logging.getLogger(__name__)


class Hubitat(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):
        """
        Required:
            server_url: Hubitat URL

        Optional:
            post_interval: Interval in seconds for posting updates to the Hubitat (default 60)

            target_unit: Unit system to use for posting to Hubitat if different than StdConvert target_unit (default None)
        """
        super().__init__(engine, config_dict)
        log.info("version %s", VERSION)

        site_dict = weewx.restx.get_site_dict(config_dict, 'Hubitat', 'server_url')
        if site_dict is None:
            return

        try:
            site_dict['manager_dict'] = weewx.manager.get_manager_dict_from_config(config_dict, 'wx_binding')
        except weewx.UnknownBinding:
            pass

        # The installer writes the placeholder hubURL_from_hubitat_device. An
        # uploader with a server_url that is not a URL raises on its first
        # packet and the thread ends. The queue would then grow with every
        # loop packet, so the thread is not started.
        server_url = site_dict['server_url']
        if not server_url.startswith(('http://', 'https://')):
            log.error("server_url is '%s'. Set it to the hubURL of the Hubitat device, "
                      "which starts with http://. Data will not be posted.", server_url)
            return

        # If we've been given a conversion target, ensure that it is valid
        target_unit = site_dict.get('target_unit')
        if target_unit and target_unit.upper() not in weewx.units.unit_constants:
            log.error("Invalid target_unit setting. See [StdConvert] for a list of available options")
            return

        self.loop_queue = queue.Queue()
        self.loop_thread = HubitatThread(self.loop_queue, **site_dict)
        self.loop_thread.start()
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
        log.info("Data will be posted to %s", server_url)

    def new_loop_packet(self, event):
        self.loop_queue.put(event.packet)


class HubitatThread(weewx.restx.RESTThread):
    _FORMATS = {
        'outTemp': ('temperature', '%.1f'),
        'outHumidity': ('humidity', '%.0f'),

        'windSpeed': ('windSpeed', '%03.1f'),
        'windDir': ('windDirection', '%03.0f'),
        'windGust': ('windGustSpeed', '%03.1f'),
        'windGustDir': ('windGustDirection', '%03.0f'),

        'appTemp': ('apptemp', '%.1f'),
        'heatindex': ('heatindex', '%.1f'),
        'humidex': ('humidex', '%.1f'),
        'windchill': ('windchill', '%.1f'),

        'rain': ('rain', '%.2f'),
        'rainRate': ('rainRate', '%.2f'),
        'hourRain': ('hourRain', '%.2f'),
        'dayRain': ('dayRain', '%.2f'),
        'rain24': ('rain24', '%.2f'),

        'barometer': ('barometer', '%.3f'),
        'dewpoint': ('dewpoint', '%.1f'),
        'cloudbase': ('cloudbase', '%.0f'),

        'UV': ('uv', '%.1f'),
        'radiation': ('radiation', '%.1f'),
        'THSW': ('THSW', '%.1f'),
    }

    def __init__(self, q, manager_dict=None,
                 server_url=None,
                 target_unit=None,
                 skip_upload=False,
                 post_interval=60, max_backlog=0, stale=None,
                 log_success=False, log_failure=False,
                 timeout=10, max_tries=1, retry_wait=1):
        """Initializer for the uploader thread.

        Args:
            q (queue.Queue): The queue that delivers the loop packets.
            manager_dict (dict|None): Arguments for opening the database manager,
                which supplies the rain totals missing from a loop packet. None
                if the station has no wx_binding.
            server_url (str): The hubURL of the Hubitat WeeWX device.
            target_unit (str|None): Name of the unit system to post in, for
                example 'METRIC'. None posts in the unit system of the packet.

        The other arguments are those of weewx.restx.RESTThread.
        """
        super().__init__(q,
                         protocol_name='Hubitat',
                         manager_dict=manager_dict,
                         post_interval=post_interval,
                         max_backlog=max_backlog,
                         stale=stale,
                         log_success=log_success,
                         log_failure=log_failure,
                         max_tries=max_tries,
                         timeout=timeout,
                         retry_wait=retry_wait,
                         skip_upload=skip_upload)

        self.server_url = server_url
        if target_unit:
            self.unit_system = weewx.units.unit_constants[target_unit.upper()]
        else:
            self.unit_system = None

    def format_url(self, _):
        """Return the URL for posting to the Hubitat"""
        log.debug("url: %s", self.server_url)
        return self.server_url

    def get_post_body(self, in_record):
        """Return the body for posting to the Hubitat"""

        # Convert the data if requested
        if self.unit_system:
            record = weewx.units.to_std_system(in_record, self.unit_system)
        else:
            record = in_record

        # Select and format the data
        data = {}
        for wkey in self._FORMATS:
            if wkey in record and record[wkey] is not None:
                key = self._FORMATS[wkey][0]
                value = self._FORMATS[wkey][1] % record[wkey]
                data[key] = value

        log.debug("post_body: %s", data)
        return json.dumps(data), 'application/json'
