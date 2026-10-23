# weewx-hubitat

A WeeWX service that posts loop data to a WeeWX device on a Hubitat hub. It sends current observations such as temperature, humidity, wind, rain and pressure as JSON over HTTP on the local network. It does not install the Hubitat side.

This is a continuation of [dennypage/weewx-hubitat](https://github.com/dennypage/weewx-hubitat). The Hubitat device driver is part of [dennypage/hubitat](https://github.com/dennypage/hubitat/tree/master/drivers/weewx) and is not copied here. See `ORIGIN.md`.

## Requirements

- A Hubitat hub that can reach the WeeWX server on the local network.
- The WeeWX device driver `weewx.groovy` on the hub, with a virtual device of that type. Follow the [driver instructions](https://github.com/dennypage/hubitat/blob/master/drivers/weewx/README.md): enter the IPv4 address of the WeeWX server in the device preferences and note the `hubURL` state variable of the device.

## Installation

Install `hubitat` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/hubitat.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

The installer adds a `[[Hubitat]]` section with a placeholder for `server_url`. Set it to the `hubURL` of the Hubitat device, for example `http://192.168.100.2:39501`, and restart WeeWX. Until then nothing is posted.

## Configuration

```
[StdRESTful]
    [[Hubitat]]
        server_url = http://192.168.100.2:39501
```

| Option | Default | Meaning |
|---|---|---|
| `server_url` | none | `hubURL` of the Hubitat device. Required. Must start with `http://` or `https://`. |
| `enable` | `true` | Set to `false` to switch the service off. |
| `post_interval` | `60` | Minimum seconds between two posts. The installer writes `60`. |
| `target_unit` | none | Unit system to post in: `US`, `METRIC` or `METRICWX`. Without it the unit system of the loop packet is used. |
| `max_backlog` | `0` | Packets that may wait in the queue before older ones are dropped. |
| `stale` | none | Age in seconds after which a packet is not posted. |
| `timeout` | `10` | Seconds to wait for the Hubitat. |
| `max_tries` | `1` | Attempts per post. |
| `retry_wait` | `1` | Seconds between attempts. |
| `log_success` | `false` | Log every post. The installer writes `false`. Without it in the section, `log_success` from the top of `weewx.conf` applies. |
| `log_failure` | top of `weewx.conf` | Log every failed post. |
| `skip_upload` | `false` | Prepare the post but do not send it. |

The attributes the device receives are listed in the [driver README](https://github.com/dennypage/hubitat/blob/master/drivers/weewx/README.md). Observations that a station does not report are left out.

## Limitations

- Tested only against a local stand-in for the Hubitat device, not against a hub or the driver.
- The service posts loop packets, not archive records. Hourly, daily and 24 hour rain come from the database when the packet lacks them.

## Development

```
python -m pytest -q tests
```

The tests need WeeWX and pytest in the Python environment.

## License

Copyright (c) 2020, Denny Page. BSD 2-Clause License, see `LICENSE`.
