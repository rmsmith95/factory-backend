import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from api.gantry import router as gantry_router
from api.cobot280 import router as cobot280_router
from api.gripper import router as gripper_router
from api.arduino import router as arduino_router
from api.jobs import router as jobs_router
from sections.factory import Factory

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gantry_router, prefix="/gantry")
app.include_router(cobot280_router, prefix="/cobot280")
app.include_router(gripper_router, prefix="/gripper")
app.include_router(arduino_router, prefix="/arduino")
app.include_router(jobs_router, prefix="/jobs")


@app.get("/")
def read_root():
    logging.info("OpenPnA backend running!")
    return {"message": "OpenPnA backend running!"}


@app.on_event("startup")
async def startup():
    logging.info("===== Initialise Factory1 =====")
    # Run blocking load_factory in a thread
    factory = await asyncio.to_thread(Factory().load_factory, "examples/factory1.json")
    app.state.factory = factory

    logging.info(f"Factory loaded: {factory}")
    logging.info(f"Jobs: {len(factory.jobs)}, Parts: {len(factory.parts)}, Machines: {len(factory.machines)}")
    logging.info(f"Machines: {factory.machines}")


@app.get("/get_health")
async def get_health():
    machines = app.state.factory.machines
    # Save factory in background to avoid blocking
    await asyncio.to_thread(app.state.factory.save_factory)

    return {
        "status": "server connected",
        "machines": {
            "gantry": machines["gantry"].is_connected(),
            "gripper": machines["gripper"].is_connected(),
            "arduino": machines["arduino"].is_connected(),
            "cobot280": machines["cobot280"].is_connected(),
        },
    }


@app.get("/factory_status")
def factory_status():
    return {"factory_initialized": app.state.factory is not None}


# --- Parts ---
@app.get("/get_parts")
def get_parts():
    """ Return all parts as a dict: partId -> part """
    return app.state.factory.parts


@app.get("/get_machines")
def get_machines():
    """Return all machines as a dict: machineId -> machine"""
    gantry = app.state.factory.machines["gantry"]
    return {
        "gantry": {'locations': gantry.locations, 'toolend': gantry.toolend, 'holders': gantry.holders },
        "cobot280": {},
        "gripper": {},
        "arduino": {},
    }


@app.get("/get_tools")
def get_tools():
    """Return all tools as a dict: toolId -> tool"""
    return app.state.factory.tools
