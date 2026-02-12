import serial
import time
import sys

# ============================
# USER SETTINGS
# ============================
PORT = "COM4"        # Change if needed
BAUD = 1_000_000     # Try 1_000_000 first, then 115200 if no response
TIMEOUT = 0.2

# ============================
# SERIAL SETUP
# ============================
try:
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        timeout=TIMEOUT,
        write_timeout=TIMEOUT
    )
except Exception as e:
    print("❌ Failed to open serial port:", e)
    sys.exit(1)

# ============================
# UTILS
# ============================
def log(msg):
    print(f"[LOG] {msg}")

def hexdump(data: bytes):
    return " ".join(f"{b:02X}" for b in data)

def checksum(data):
    """
    ST-series checksum:
    ~(ID + LEN + INST + PARAMS) & 0xFF
    """
    return (~(sum(data) & 0xFF)) & 0xFF

# ============================
# PACKET SENDER
# ============================
def send_packet(servo_id, instruction, params=None, label=""):
    if params is None:
        params = []

    length = 2 + len(params)  # instruction + checksum
    packet = [
        0xFF, 0xFF,
        servo_id,
        length,
        instruction,
        *params
    ]

    packet.append(checksum(packet[2:]))
    raw = bytes(packet)

    log(f"{label} TX -> {hexdump(raw)}")
    ser.write(raw)
    ser.flush()

    time.sleep(0.03)

    rx = ser.read(64)
    if rx:
        log(f"{label} RX <- {hexdump(rx)}")
    else:
        log(f"{label} RX <- <no response>")

    time.sleep(0.05)

# ============================
# TEST ROUTINES
# ============================
def test_ping():
    log("=== PING TEST ===")
    for sid in [0, 1]:
        send_packet(sid, 0x01, label=f"PING ID={sid}")
        send_packet(sid, 0x02, label=f"PING2 ID={sid}")

def test_move():
    log("=== MOVE TEST ===")

    pos = 2000      # mid range
    speed = 500

    params = [
        pos & 0xFF,
        (pos >> 8) & 0xFF,
        speed & 0xFF,
        (speed >> 8) & 0xFF
    ]

    for sid in [0, 1]:
        send_packet(sid, 0x03, params, label=f"MOVEv1 ID={sid}")
        send_packet(sid, 0x04, params, label=f"MOVEv2 ID={sid}")

# ============================
# MAIN
# ============================
log("Opening serial port")
time.sleep(0.2)

test_ping()
time.sleep(0.5)

test_move()

log("Done")
ser.close()
