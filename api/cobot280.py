from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List
router = APIRouter()


class ConnectRequest(BaseModel):
    method: str
    com: str
    baud: int = 115200
    ip: str = '10.163.187.60'
    port: int = 8000
    timeout: float = 3.0  # seconds

class SetAnglesRequest(BaseModel):
    angles: List[float]
    speed: int = 50

class SetAngleRequest(BaseModel):
    jointIndex: int
    deltaValue: float
    speed: int = 50

# --- Test connection endpoint ---
@router.post("/connect")
def connect(req: ConnectRequest, request: Request):
    cobot280 = request.app.state.factory.machines['cobot280']
    return cobot280.connect(req.method, req.ip, req.port, req.com, req.baud)

# --- Set angles ---
@router.post("/set_angle")
def set_angles(req: SetAngleRequest, request: Request):
    cmd = {"command": "set_angle", "jointIndex": req.jointIndex, "deltaValue": req.deltaValue, "speed": req.speed}
    cobot280 = request.app.state.factory.machines['cobot280']
    return cobot280.send_command_to_pi(cmd)

# --- Set angles ---
@router.post("/set_angles")
def set_angles(req: SetAnglesRequest, request: Request):
    if len(req.angles) != 6:
        return {"status": "error", "message": "'angles' must be a list of 6 values"}
    cmd = {"command": "set_angles", "angles": req.angles, "speed": req.speed}
    cobot280 = request.app.state.factory.machines['cobot280']
    return cobot280.send_command_to_pi(cmd)


@router.get("/get_position")
def get_position(request: Request):
    cobot280 = request.app.state.factory.machines['cobot280']
    cmd = {"command": "get_position"}
    values = cobot280.send_command_to_pi(cmd)
    print(values)
    return {"angles": values, "status": "ok"}
