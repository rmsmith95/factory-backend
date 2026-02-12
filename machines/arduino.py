import serial
import time
import logging
from sections.utils import Connection, Pose


class Arduino:
    def __init__(self):
        self.connection = None

    def connect(self, method, ip, port, com, baud, timeout=3):
        """Connect to Arduino via serial"""
        self.connection = Connection(method, ip, port, com, baud, timeout)
        logging.warning(f'{self.connection}')
        if self.connection.serial is not None and self.connection.serial.is_open:
            self.connection.serial.close()

        self.connection.serial = serial.Serial(com, baud, timeout=timeout)
        time.sleep(2)
        logging.info(f"Connected to Arduino on {com}")
        return {"status": "connected", "com": com, "baud": baud}

    def is_connected(self) -> bool:
        if self.connection:
            self.connection.connected = self.connection.serial is not None and self.connection.serial.is_open
            return self.connection.connected
        return False
    
    def screw(self, direction: str, duration: float = 0, speed: int = 150):
        """
        duration: seconds (ignored for STOP)
        speed: 0-255 PWM value for ENA
        """
        if not self.is_connected():
            logging.info(f"Arduino not connected")
            raise RuntimeError("Arduino not connected")

        if direction.upper() == "STOP":
            cmd = "STOP"
        else:
            duration_ms = int(duration * 1000)
            cmd = f"{direction.upper()}"

        # clear buffer and send command
        logging.info(f"arduino screwdriver cmd:{cmd}")
        self.connection.serial.reset_input_buffer()
        self.connection.serial.write(cmd.encode("ascii"))

        # read Arduino response (non-blocking)
        time.sleep(duration + 0.05)  # allow motor to run
        lines = []
        while self.connection.serial.in_waiting:
            lines.append(self.connection.serial.readline().decode(errors="ignore").strip())

        return lines
