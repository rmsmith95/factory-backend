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


class UnlockRequest(BaseModel):
    time_s: float  # seconds to unlock


@router.post("/unlock")
def unlock(req: UnlockRequest, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    rpi.unlock(UnlockRequest.time_s)
    return {"status": "completed"}


class Screw(BaseModel):
    duration: int
    speed: int


@router.post("/screw_cw")
def screw_cw(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("CW", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/screw_ccw")
def screw_ccw(req: Screw, request: Request):
    rpi = request.app.state.factory.machines['rpi']
    # lines = rpi.screw("CCW", req.duration, req.speed)
    lines = rpi.screw("CCW", req.duration, req.speed)
    return {"status": "completed", "response": lines}


@router.post("/screw_stop")
def screw_stop(request: Request):
    rpi = request.app.state.factory.machines['rpi']
    lines = rpi.screw("STOP")
    return {"status": "completed", "response": lines}
