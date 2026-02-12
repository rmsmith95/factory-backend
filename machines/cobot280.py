import socket
import logging
import json
from typing import List
from sections.utils import Connection, Pose


class Cobot280:
    def __init__(self):
        self.connection = Connection()
        self.pose = None
        pass

    def send_command_to_pi(self, cmd: dict):
        """ Sends a JSON command to the Pi over TCP and returns the JSON response. """
        if self.connection.ip == "":
            return {"cmd": cmd, "status": "error", "message": "no ip"}

        print(f"Sending command to Pi: {cmd} @ {self.connection.ip}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.connection.timeout)
                s.connect((self.connection.ip, self.connection.port))
                s.sendall((json.dumps(cmd) + "\n").encode())

                resp = s.recv(1024).decode().strip()
                return json.loads(resp)

        except Exception as e:
            logging.error(f"Failed to send command to Pi ({self.connection.ip}): {e}")
            return {"status": "error", "message": str(e)}

    def connect(self, method, ip, port, com, baud, timeout=3):
        """ Test connection by requesting current positions. """
        self.connection = Connection(method, ip, port, com, baud, timeout)
        resp = self.send_command_to_pi({"command": "get_position"})
        self.connection.connected = (
            isinstance(resp, dict) and
            resp.get("status") == "ok"
        )
        return resp
    
    def is_connected(self) -> bool:
        return self.connection.connected

    def get_position(self) -> List[float]:
        """ Returns current joint positions as a list of 6 floats. """
        cmd = {"command": "get_position"}
        resp = self.send_command_to_pi(cmd)
        if resp.get("status") == "ok" and "angles" in resp:
            return resp["angles"]
        return []

    def set_angle(self, joint_index: int, delta_value: float, speed: float):
        """ Increment a single joint by delta_value. """
        cmd = {
            "command": "set_angle",
            "jointIndex": joint_index,
            "deltaValue": delta_value,
            "speed": speed
        }
        return self.send_command_to_pi(cmd)

    def set_angles(self, angles: List[float], speed: float):
        """ Set all joints to the given angles. """
        if len(angles) != 6:
            return {"status": "error", "message": "'angles' must be a list of 6 values"}
        cmd = {
            "command": "set_angles",
            "angles": angles,
            "speed": speed
        }
        return self.send_command_to_pi(cmd)

    def move_to(self, angles: List[float], speed: float):
        """Alias for set_angles, for clarity. """
        return self.set_angles(angles, speed)
