import logging
import threading
import requests
import time
import re

class Gantry:
    def __init__(self, host="192.168.1.60"):
        self.host = host
        self.base_url = f"http://{self.host}/printer/gcode/script"
        self.toolend = {'position': {'x': 0, 'y': 0, 'z': 0, 'a': 0}}
        self._io_lock = threading.Lock()
        self.in_motion = False
    
    def connect(self, method, ip, port, com, baud):
        pass
    
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
        """Fetches current position using M114 (Standard Klipper G-code)."""
        # M114 is the standard Klipper command for G-code position
        res = self.send("M114")
        logging.info(f'M114 result: {res}')
        if not res: 
            return False
        
        # Klipper M114 typically returns: "X:0.00 Y:0.00 Z:0.00 E:0.00 Count X:0 Y:0 Z:0"
        # This regex captures the axis letter and its float value, ignoring "Count"
        try:
            matches = re.findall(r"([XYZE]):\s*([-?\d.]+)", res)
            coords = {k.lower(): float(v) for k, v in matches}
            
            if coords:
                # Update the internal state and return the new pose
                if 'position' not in self.toolend:
                    self.toolend['position'] = {}
                self.toolend['position'].update(coords)
                return coords
                
        except Exception as e:
            logging.error(f"Failed to parse M114 response '{res}': {e}")
            
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
