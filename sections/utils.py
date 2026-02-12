from typing import List


class Connection:
    def __init__(self, method='', ip='',port=8000,com='',baud=115200,timeout=3):
        self.method = method
        self.ip = ip
        self.port = port
        self.com = com
        self.baud = baud
        self.timeout = timeout
        self.serial = None
        self.connected = False


class Pose:
    def __init__(self, x: float, y: float, z: float,
                 yaw: float = 0, pitch: float = 0, roll: float = 0):
        self.x = x
        self.y = y
        self.z = z
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll

    def __add__(self, other: "Pose") -> "Pose":
        if not isinstance(other, Pose):
            raise TypeError("Can only add another Pose object")
        return Pose(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
            self.yaw + other.yaw,
            self.pitch + other.pitch,
            self.roll + other.roll,
        )

    def __str__(self) -> str:
        return f"Pose({self.x}, {self.y}, {self.z}, {self.yaw}, {self.pitch}, {self.roll})"

    def __repr__(self) -> str:
        return self.__str__()

    def get(self):
        return (self.x, self.y, self.z, self.yaw, self.pitch, self.roll)

    def set(self, x, y, z, yaw=0, pitch=0, roll=0):
        self.x, self.y, self.z = x, y, z
        self.yaw, self.pitch, self.roll = yaw, pitch, roll


class Size:
    def __init__(self, x: float, y: float, z: float):
        self.x, self.y, self.z = x, y, z

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __repr__(self):
        return f"Size({self.x}, {self.y}, {self.z})"


class Action:
    def __init__(self, initial_pose: Pose, target_pose: Pose):
        self.initial_pose = initial_pose
        self.target_pose = target_pose

    def __repr__(self):
        return f"Action(from={self.initial_pose}, to={self.target_pose})"


class Interface:
    def __init__(self, type_: str, pose: Pose, actions: List[Action] = None):
        self.type = type_
        self.pose = pose
        self.actions = actions or []

    def __repr__(self):
        return f"Interface(type={self.type}, pose={self.pose}, actions={len(self.actions)})"
