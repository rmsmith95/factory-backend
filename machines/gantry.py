import logging
import threading
import requests
import time
import re
from sections.utils import Connection


class Gantry:
    def __init__(self):
        self.connection = None
        self.base_url = ""
        self.toolend = {'position': {'x': 0, 'y': 0, 'z': 0, 'a': 0}}
        self._io_lock = threading.Lock()
        self.in_motion = False
    
    def connect(self, method, ip, port, com, baud):
        self.connection = Connection(method, ip, port, com, baud, timeout=5)
        self.base_url = f"http://{ip}/printer/gcode/script"
    
    def is_connected(self):
        return True

    def send(self, cmd):
        """Thread-safe G-code dispatch via Moonraker API."""
        with self._io_lock:
            try:
                # Moonraker expects JSON for the script endpoint
                response = requests.post(self.base_url, json={"script": cmd}, timeout=5)
                response.raise_for_status()
                # Klipper returns an 'ok' or the command output in 'result'
                return response.json().get('result', "")
            except Exception as e:
                logging.error(f"G-code failed: {cmd} | Error: {e}")
                return None

    def get_pose(self):
        """Fetches X, Y, Z from gcode_move and A from the custom stepper object."""
        # Query both gcode_move and your specific 'a' stepper
        query_url = f"http://{self.connection.ip}/printer/objects/query?gcode_move&manual_stepper%20a"
        
        try:
            response = requests.get(query_url, timeout=5)
            response.raise_for_status()
            status = response.json()['result']['status']
            
            # 1. Get X, Y, Z from the standard gcode_position array [x, y, z, e]
            gcode_pos = status['gcode_move']['gcode_position']
            
            # 2. Get A from your custom manual_stepper object
            # Note: In Moonraker, manual steppers are usually under 'manual_stepper <name>'
            # a_pos = status.get('manual_stepper a', {}).get('position', 0.0)
            
            coords = {
                'x': float(gcode_pos[0]),
                'y': float(gcode_pos[1]),
                'z': float(gcode_pos[2]),
                'a': float(0)
            }
            
            # Update internal state
            if 'position' not in self.toolend:
                self.toolend['position'] = {}
            self.toolend['position'].update(coords)
            
            return coords

        except Exception as e:
            logging.error(f"Failed to fetch XYZA position: {e}")
            return False
        
    def home(self):
        """Sets internal coordinate system origin (G92)."""
        logging.info(f"Homing...")
        return self.send(f"G28")

    def set_position(self, x, y, z, a):
        """Sets internal coordinate system origin (G92)."""
        logging.info(f"Setting logical position to X{x} Y{y} Z{z} A{a}")
        return self.send(f"G92 X{x} Y{y} Z{z} A{a}")

    def _goto_task(self, x, y, z, a, speed):
        """Internal background task for motion."""
        try:
            self.send("G90") # Ensure Absolute Positioning
            self.send(f"G1 X{x} Y{y} Z{z} A{a} F{speed}")
            self.send("M400") # Wait for moves to finish
        finally:
            self.in_motion = False

    def goto(self, x, y, z, a, speed):
        """Non-blocking motion API."""
        if self.in_motion:
            logging.warning("Gantry already in motion.")
            return False
        
        self.in_motion = True
        t = threading.Thread(target=self._goto_task, args=(x, y, z, a, speed), daemon=True)
        t.start()
        return True

    def step(self, x=0, y=0, z=0, a=0, speed=1000):
        """Incremental move (G91)."""
        self.send("G91") # Relative Positioning
        res = self.send(f"G1 X{x} Y{y} Z{z} A{a} F{speed}")
        self.send("G90") # Return to Absolute safely
        return res
