# backend/api/server.py
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
    ip: str = ''
    port: int = 8000
    timeout: float = 3.0  # seconds

@router.post("/connect")
def connect(req: ConnectRequest, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    connected = rpi.connect(req.method, req.ip, req.port, req.com, req.baud)
    return {
        "connected": connected,
        "status": rpi.status
    }


class UnlockRequest(BaseModel):
    time_s: float  # seconds to unlock


@router.post("/unlock")
def unlock(req: UnlockRequest, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    rpi.unlock(UnlockRequest.time_s)
    return {"status": "completed"}


class Screw(BaseModel):
    duration: float
    speed: float


@router.post("/motor_cw")
def motor_cw(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("CW", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/motor_ccw")
def motor_ccw(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    # lines = rpi.screw("CCW", req.duration, req.speed)
    lines = rpi.screw("CCW", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/motor_stop")
def motor_stop(request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("STOP")
    return {"status": "completed", "response": lines}
