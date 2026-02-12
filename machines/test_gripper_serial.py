import serial
import time

# ===============================
# CONFIG
# ===============================
PORT = "COM4"       # set your ESP32 COM port
BAUD = 115200
SERVO_ID = 1

# ===============================
# CHECKSUM
# ===============================
def calc_checksum(data):
    s = sum(data[2:-1]) & 0xFF
    return (~s) & 0xFF

# ===============================
# PACKET SEND
# ===============================
def send_packet(ser, packet):
    packet[-1] = calc_checksum(packet)
    ser.write(packet)
    ser.flush()
    time.sleep(0.03)

def write_position(ser, position, speed=200):
    packet = bytearray([
        0xFF, 0xFF,
        SERVO_ID,
        0x07,
        0x03,
        0x2A,
        position & 0xFF,
        (position >> 8) & 0xFF,
        speed & 0xFF,
        (speed >> 8) & 0xFF,
        0,0,0
    ])
    send_packet(ser, packet)

def read_data(ser, addr, length):
    packet = bytearray([
        0xFF, 0xFF,
        SERVO_ID,
        0x04,
        0x02,
        addr,
        length,
        0
    ])
    send_packet(ser, packet)

    start = time.time()
    while ser.in_waiting < (6 + length):
        if time.time() - start > 0.3:
            return None

    header = ser.read(4)
    data = ser.read(header[3])
    return data[1:length+1]  # skip error byte

# ===============================
# TEST CODE
# ===============================
def main():
    print("Opening serial port…")
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(2)  # wait for ESP32 reset

    print("Sweeping servo positions…")
    for pos in [1024, 2048, 3072, 2048]:
        print(f" → Moving to {pos}")
        write_position(ser, pos)
        time.sleep(1.2)

        dv = read_data(ser, 0x38, 2)
        if dv:
            pos_value = dv[0] | (dv[1] << 8)
            print(f"   Position read: {pos_value}")

        vv = read_data(ser, 0x2F, 1)
        if vv: print(f"   Voltage x0.1V → {vv[0]}")

        tv = read_data(ser, 0x2E, 1)
        if tv: print(f"   Temp C → {tv[0]}")

    print("Done!")
    ser.close()

if __name__ == "__main__":
    main()
