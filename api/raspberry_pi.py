# backend/machines/tool_changer.py
# import serial
import time
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()
rpi = None  # global persistent serial object

class ConnectRequest(BaseModel):
    method: str
    com: str
    baud: int = 115200
    ip: str = '10.163.187.60'
    port: int = 8000
    timeout: float = 3.0  # seconds

@router.post("/connect")
def connect(req: ConnectRequest, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    return rpi.connect(req.method, req.ip, req.port, req.com, req.baud)

def send_cmd(cmd: str):
    if rpi is None or not rpi.is_open:
        raise HTTPException(status_code=400, detail="RPi not connected")
    rpi.write((cmd + "\n").encode())
    time.sleep(0.05)


class UnlockRequest(BaseModel):
    time_s: float  # seconds to unlock


@router.post("/unlock")
def unlock(req: UnlockRequest):
    send_cmd("ON")
    time.sleep(req.time_s)
    send_cmd("OFF")
    time.sleep(1)
    return {"status": "completed"}


class Screw(BaseModel):
    duration: int
    speed: int

@router.post("/screw_clockwise")
def screw_clockwise(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("FWD", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/screw_reverse")
def screw_reverse(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    # lines = rpi.screw("CCW", req.duration, req.speed)
    lines = rpi.screw("BKW", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/screwdriver_stop")
def screwdriver_stop(request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("STOP")
    return {"status": "completed", "response": lines}
