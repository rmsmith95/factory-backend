import serial
import time
import logging
import re
from sections.utils import Connection, Pose
import threading


class Gantry:
    def __init__(self):
        self.connection = Connection()
        self.pose = None
        self.holders = []
        self.locations = []
        self.toolend = None
        self._io_lock = threading.Lock()


    def connect(self, method, ip, port, com, baud, timeout=3):
        # close existing serial if open
        if self.connection and self.connection.serial:
            if self.connection.serial.is_open:
                self.connection.serial.close()

        self.connection = Connection(method, ip, port, com, baud, timeout)
        self.connection.serial = serial.Serial(com, baud, timeout=timeout)
        self.set_position(**self.toolend['position'])
        logging.info(f"Connected to TinyG on {com}")
        return True

    def is_connected(self) -> bool:
        if self.connection:
            self.connection.connected = self.connection.serial is not None and self.connection.serial.is_open
            return self.connection.connected
        return False

    def send(self, command, delay=0.05):
        if not self.is_connected():
            return False

        with self._io_lock:
            self.connection.serial.write((command + "\n").encode())
            time.sleep(delay)
            # return self.read_response()
            lines = []
            while self.connection.serial.in_waiting:
                lines.append(
                    self.connection.serial.readline().decode(errors="ignore").strip()
                )
            return lines


    def get_info(self):
        if not self.is_connected():
            return False
        lines = self.send("?")
        info = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "a": 0.0,
            "feedrate": 0.0,
            "velocity": 0.0,
            "machine_state": None,
        }
        if not lines:
            return False

        for line in lines:
            if line.startswith("X position"):
                info["x"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("Y position"):
                info["y"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("Z position"):
                info["z"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("A position"):
                info["a"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("Feed rate"):
                info["feedrate"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("Velocity"):
                info["velocity"] = float(re.findall(r"[-\d.]+", line)[0])
            elif line.startswith("Machine state"):
                info["machine_state"] = line.split(":", 1)[1].strip()

        if self.toolend['position']:
            self.toolend['position'] = {'x': info['x'], 'y':info['y'], 'z':info['z'], 'a':info['a']}
        logging.debug(f"get_info: {info}")
        return info


    def set_position(self, x, y, z, a):
        logging.info(f"set_position {x, y, z, a}")
        return self.send(f"G92 X{x} Y{y} Z{z} A{a}")

    def _goto(self, x, y, z, a, speed):
        """Run motion in background thread"""
        self.in_motion = True
        try:
            self.send("G90")
            self.send(f"G1 X{x} Y{y} Z{z} A{a} F{speed}")
        finally:
            self.in_motion = False
        logging.info(f"goto {x, y, z, a, speed}")

    def goto(self, x, y, z, a, speed):
        """Non-blocking API: motion runs in background"""
        t = threading.Thread(target=self._goto, args=(x, y, z, a, speed), daemon=True)
        t.start()
        return True

    def step(self, x, y, z, a, speed):
        self.send("G91")
        return self.send(f"G1 X{x} Y{y} Z{z} A{a} F{speed}")

    def unlock(self, time_s: float):
        self.send("M8")
        time.sleep(time_s)
        self.send("M9")

    def reset(self):
        self.connection.serial.write(b"\x18")
        time.sleep(0.2)
    
    def detach(self, target=None):
        """detach current end effector to target holder"""
        target_holder = None
        if target is None:
            for holder in self.holders:
                if holder.effector == "":
                    target_holder = holder
                    break
        else:
            for holder in self.holders:
                if holder.name == target:
                    target_holder = holder
                    break

        if target_holder is None:
            return False
        
        holder_out_pose = self.locations[f"{target}_out"]
        self.goto(holder_out_pose)
        time.sleep(10)
        holder_in_pose = self.locations[f"{target}_in"]
        self.goto(holder_in_pose)
        time.sleep(3)
        self.unlock()
        time.sleep(1)
        self.goto(holder_out_pose)
        return True
    
    def attach(self, target):
        """attach end effector from its holder to the toolend. detach first if required"""
        if self.toolend.effector != "":
            self.detach()
        
        target_holder = None
        for holder in self.holders:
            if holder.name == target:
                target_holder = holder

        if target_holder is None:
            return False
        
        holder_out_pose = self.locations[f"{target}_out"]
        self.goto(holder_out_pose)
        time.sleep(10)
        holder_in_pose = self.locations[f"{target}_in"]
        self.goto(holder_in_pose)
        time.sleep(3)
        self.unlock()
        time.sleep(1)
        self.goto(holder_out_pose)
        return True

