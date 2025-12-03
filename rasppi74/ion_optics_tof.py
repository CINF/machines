""" Ion Optics Control for TOF """
import time
from PyExpLabSys.apps.ion_optics_controller import CursesTui as CursesTui
from PyExpLabSys.apps.ion_optics_controller import IonOpticsControl as IonOpticsControl

def main():
    """ Main function """
    # The ordering of the list will set the corresponding channel number
    lenses = ['lens_a', 'lens_b', 'lens_c', 'lens_d', 'lens_e', '', 'focus', 'extraction']
    port = '/dev/serial/by-id/usb-Stahl_Electronics_HV_Series_HV069-if00-port0'
    ioc = IonOpticsControl(port, 'TOF', lenses)
    ioc.start()
    time.sleep(1)

    tui = CursesTui(ioc)
    tui.daemon = True
    tui.start()

    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            tui.stop()
            ioc.quit = True
            break

if __name__ == '__main__':
    main()
