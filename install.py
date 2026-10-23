# Installer for the Hubitat device extension
#
# Modified 2026-10-23 by weewx-packages: version 1.1.

from weecfg.extension import ExtensionInstaller

def loader():
    return HubitatInstaller()

class HubitatInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version="1.1",
            name='hubitat',
            description='Post loop data to a Hubitat device',
            restful_services='user.hubitat.Hubitat',
            config={
                'StdRESTful': {
                    'Hubitat': {
                        'server_url': 'hubURL_from_hubitat_device',
                        'post_interval': '60',
                        'log_success': False}}},
            files=[('bin/user', ['bin/user/hubitat.py'])]
        )
