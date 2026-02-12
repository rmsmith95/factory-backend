from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import asyncio
from typing import List
import logging


router = APIRouter(tags=["gantry"])

# ============================================================
# API MODELS
# ============================================================

class ConnectRequest(BaseModel):
    method: str
    com: str
    baud: int = 115200
    ip: str = '10.163.187.60'
    port: int = 8000
    timeout: float = 3.0  # seconds

class SetPositionRequest(BaseModel):
    x: float
    y: float
    z: float
    a: float

class MoveXYZRequest(BaseModel):
    x: float
    y: float
    z: float
    a: float
    speed: float  # mm/min

class UnlockRequest(BaseModel):
    time_s: float

class RawCommandRequest(BaseModel):
    command: str
    delay: float = 0.05

class DetachRequest(BaseModel):
    target: str

class AttachRequest(BaseModel):
    target: str

# ============================================================
# ROUTES
# ============================================================

@router.post("/connect")
async def connect(req: ConnectRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    try:
        await asyncio.to_thread(
            gantry.connect, req.method, req.ip, req.port, req.com, req.baud
        )
        return {"status": "connected", "device": "gantry"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_info")
async def get_info(request: Request):
    gantry = request.app.state.factory.machines.get("gantry")
    if not gantry:
        return {"connected": False}

    try:
        info = await asyncio.to_thread(gantry.get_info)
        return {"connected": True, **info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set_position")
async def set_position(req: SetPositionRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(gantry.set_position, req.x, req.y, req.z, req.a)
    return {"status": "ok"}


@router.post("/goto")
async def goto(req: MoveXYZRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    # Step movement in background thread
    await asyncio.to_thread(
        gantry.goto, req.x, req.y, req.z, req.a, req.speed
    )

    return {"status": "ok", "target": req.dict()}


@router.post("/step")
async def step(req: MoveXYZRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(
        gantry.step, req.x, req.y, req.z, req.a, req.speed
    )
    return {"status": "ok", "delta": req.dict()}


@router.post("/unlock")
async def unlock(req: UnlockRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(gantry.unlock, req.time_s)
    return {"status": "completed"}


@router.post("/reset")
async def reset(request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(gantry.reset)
    return {"status": "ok"}

class Location(BaseModel):
    name: str
    x: float
    y: float
    z: float
    a: float

class EditLocationsRequest(BaseModel):
    locations: List[Location]

@router.post("/edit_locations")
async def edit_locations(req: EditLocationsRequest, request: Request):
    gantry = request.app.state.factory.machines.get('gantry')
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    # Update the gantry's locations safely in a thread
    async def update_locations():
        gantry.locations = [loc.dict() for loc in req.locations]
        await asyncio.to_thread(lambda: None)  # placeholder if gantry needs real sync save

    await update_locations()
    # logging.info(f"locations: {req.locations}")
    return {"status": "ok", "locations": gantry.locations}


@router.post("/detach")
async def detach(req: DetachRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(gantry.detach, req.target)
    return {"status": "completed"}


@router.post("/attach")
async def attach(req: AttachRequest, request: Request):
    gantry = request.app.state.factory.machines['gantry']
    if not gantry:
        raise HTTPException(400, "Gantry not connected")

    await asyncio.to_thread(gantry.attach, req.target)
    return {"status": "completed"}
