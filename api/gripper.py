from fastapi import APIRouter, Request
from pydantic import BaseModel
router = APIRouter(tags=["gripper"])


class ConnectRequest(BaseModel):
    method: str
    com: str
    baud: int = 115200
    ip: str = '10.163.187.60'
    port: int = 8000
    timeout: float = 3.0  # seconds


class GripperCommand(BaseModel):
    time_s: float = 2.0
    speed: int = 1000


class SetSpeed(BaseModel):
    speed: int = 1000


@router.post("/connect")
def connect(req: ConnectRequest, request: Request):
    gripper = request.app.state.factory.machines['gripper']
    connected = gripper.connect(req.method, req.ip, req.port, req.com, req.baud)
    return {
        "connected": connected,
        "status": gripper.status
    }


@router.post("/gripper_open")
def gripper_open(cmd: GripperCommand, request: Request):
    gripper = request.app.state.factory.machines['gripper']
    return gripper.open(cmd.time_s, cmd.speed)


@router.post("/gripper_close")
def gripper_close(cmd: GripperCommand, request: Request):
    gripper = request.app.state.factory.machines['gripper']
    return gripper.close(cmd.time_s, cmd.speed)


@router.post("/speed_up")
def speed_up(request: Request):
    gripper = request.app.state.factory.machines['gripper']
    return gripper.speed_up()


@router.post("/speed_down")
def speed_down(request: Request):
    gripper = request.app.state.factory.machines['gripper']
    return gripper.speed_down()


@router.post("/set_speed")
def set_speed(cmd: SetSpeed, request: Request):
    gripper = request.app.state.factory.machines['gripper']
    gripper.set_speed(cmd.speed)
    return {"ok": True}


@router.get("/get_status")
def get_status(request: Request):
    gripper = request.app.state.factory.machines['gripper']
    return gripper.get_status() if gripper else {}
