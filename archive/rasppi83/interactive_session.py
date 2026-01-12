import serial
import time

def main():
    # MODIFY THIS PATH if needed
    port = '/dev/ttyACM0'
    # Or whatever your actual port is:
    # port = '/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_00000000_DI-2008-if00'
    
    # Open serial connection
    ser = serial.Serial(port=port, baudrate=115200, timeout=0.5)
    print(f"Connected to {port}")
    
    try:
        while True:
            # Prompt user for command
            cmd = input("DI-2008> ").strip()
            if cmd.lower() in ("exit", "quit", "q"):
                print("Exiting...")
                break
            if cmd == "":
                continue

            # Send command
            ser.write((cmd + '\r').encode())

            # Give device a moment to respond if not acquiring
            time.sleep(0.1)

            # Read all available response lines
            print("--- Response ---")
            while True:
                if ser.in_waiting == 0:
                    break
                line = ser.readline().decode(errors='ignore').strip()
                if line:
                    print(line)
            print("---------------")

    finally:
        ser.close()
        print("Serial connection closed.")

if __name__ == "__main__":
    main()

