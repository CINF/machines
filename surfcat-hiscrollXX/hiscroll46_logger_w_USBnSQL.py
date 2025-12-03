from __future__ import print_function
from sys import stdout
from time import sleep
CURSOR_BACK_2 = '\x1b[2D'
ERASE_TO_END_OF_LINE = '\x1b[0K'
from datetime import datetime
import os
from PyExpLabSys.drivers.pfeiffer_hiscroll import PfeifferHiscroll

PUMP = PfeifferHiscroll('/dev/ttyUSB0', device_address=2)

def main():
    #DataSaver 
    _file_name = 'HiScroll46'
    start_time = datetime.now()
    make_local_backup = True
    if make_local_backup:
        try:
            _folder_name = '/media/data1/'+_file_name+'/'
            os.mkdir(_folder_name)
            print(_folder_name)
        except(FileExistsError):
            pass
        except Exception as e:
            print(e)

    log_name = _folder_name+_file_name+'_'+str(start_time.year)+'_'+str(start_time.month)+'_'+str(start_time.day)+'_'+str(start_time.hour)+'_'+str(start_time.minute)+'.csv'
    try:
        header_string = '    Date      Time    Pressure [hPa] Pressure Set [hPa] Speed [rpm] Speed Set [rpm] Speed Nom [rpm] Temp Final Stage [C] Temp Pump \
[C] Temp Contr [C] Power [W] Current [A] Voltage [V] Operating Hours [h]'
        header_write_string = 'Pressure [hPa]; Pressure Set [hPa]; Speed [rpm]; Speed Set [rpm]; Speed Nom [rpm]; Temp Final Stage [C]; Temp Pump [C]; Temp \
Contr [C]; Power [W]; Current [A]; Voltage [V]; Operating Hours [h]'
        try:
            datafile =  open(log_name, 'a')
            datafile.write('Timestamp;')
            datafile.write(header_write_string)
            datafile.write('\n')


        except(KeyError):
            print('Not saving to Harddisk')
            pass

        print('Starting to log... Press Ctrl-C to stop\n\n')
        sleep(1)
        print(header_string)

        try:
            read_and_display_data(PUMP, datafile)

        except KeyboardInterrupt:
            # Clear the '^C' from the display.                                                                                                               
            print(CURSOR_BACK_2, ERASE_TO_END_OF_LINE, '\n')
            print('Stopping')
            datafile.close()

    except (PUMP, ValueError) as err:
        print('\n', err)


def read_and_display_data(PUMP, datafile):

    datafile = datafile
    while True:
        _now = datetime.now()
        _hours = PUMP.read_run_hours()
        _power_info = PUMP.drive_power()
        _power = _power_info['power']
        _current = _power_info['current']
        _voltage = _power_info['voltage']
        _speeds = PUMP.rotational_speed()
        _temps = PUMP.read_pump_temperature()
        _pressure_setpoint = PUMP.pressure_setpoint()
        _pressure_actual = PUMP.pressure()
        #string = f'{_now},{hours},{power},{current},{voltage},{speeds["actual"]},{speeds["setpoint"]},{speeds["nominal"]},{temps["pump"]},{temps["controller"]},{temps["final_stage"]},{pressure_setpoint},{pressure}'                                                                                                  
        print_string = '{}:    {:1.1E} hPa        {:1.1E} hPa    {:4.0f} rpm        {:4.0f} rpm        {:4.0f} rpm              {:4.2f} C       {:4.2f} C   \
     {:4.2f} C  {:4.2f} W      {:2.2f} A    {:3.2f} V     {:6.0f} h '.format(_now.strftime("%Y-%m-%d %H:%M:%S"),_pressure_actual,_pressure_setpoint,_speeds["actual"],_speeds["setpoint"],_speeds["nominal"],_temps["final_stage"],_temps["pump"],_temps["controller"],_power,_current,_voltage,_hours)
        write_string = '{:.5f};{:.5f};{:.5f};{};{};{};{};{};{};{};{};{};'.format(_pressure_actual,_pressure_setpoint,_speeds["actual"],_speeds["setpoint"],_speeds["nominal"],_temps["final_stage"],_temps["pump"],_temps["controller"],_power,_current,_voltage,_hours)
        print(print_string, end='\r')

        datafile.write(f'{_now};')
        datafile.write(write_string)
        datafile.write('\r\n')
        stdout.flush()
        sleep(0.5)


if __name__ == '__main__':
    main()


