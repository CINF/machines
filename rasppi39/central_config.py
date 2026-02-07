# This is a config file for the monitoring of the Vortes gas centrals in B307 first floor.
# Access as central[1]['settings']['port'] or central[1]['codenames'][3] for example..
CENTRAL = {
    # Central 1
    1: {
        'name': 'B307_basement_vortex_1',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_CO_139_1',
            2: 'B307_gasalarm_CO2_139_1',
            3: 'B307_gasalarm_H2_139_1',
            4: 'B307_gasalarm_CO_139_2',
            5: 'B307_gasalarm_CO2_139_2',
            6: 'B307_gasalarm_H2_139_2',
            7: 'B307_gasalarm_CO2_147',
            8: 'B307_gasalarm_CO_147',
            9: 'B307_gasalarm_H2_147',
            10: 'B307_gasalarm_CO_149',
            11: 'B307_gasalarm_CO2_149',
            12: 'B307_gasalarm_H2_149',
        },
        'settings': {# USB settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_AU05T6IH-if00-port0',#'/dev/ttyUSB2',
            'slave': 1,
        },
    },
    # Central 2
    2: {
        'name': 'B307_basement_vortex_2',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_fireloop_1stfloor2',
            2: 'B307_gasalarm_H2_137',
            3: 'B307_gasalarm_CO_137',
            4: 'B307_gasalarm_CO2_137',
        },
        'settings': {# USB settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_AU05SAPM-if00-port0',#'/dev/ttyUSB1',
            'slave': 1,
        },
    },
}
