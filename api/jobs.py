import logging
import asyncio
from fastapi import APIRouter, Request
from fastapi import FastAPI
from pydantic import BaseModel
router = APIRouter(tags=["jobs"])

logging.basicConfig(level=logging.INFO)


@router.post("/add_job")
async def add_job(request: Request):
    job_id = await asyncio.to_thread(request.app.state.factory.add_job)
    # logging.info(f'add_job: "{job_id}"')
    return {"status": "ok", "job_id": job_id}


class UpdateJobRequest(BaseModel):
    job: dict


@router.post("/update_job")
async def update_job(req: UpdateJobRequest, request: Request):
    logging.info(f'update_job')
    job_id = await asyncio.to_thread(request.app.state.factory.update_job, req.job)
    return {"status": "ok", "job_id": job_id}


class DeleteJobRequest(BaseModel):
    job_id: str


@router.post("/delete_job")
async def delete_job(req: DeleteJobRequest, request: Request):
    deleted = await asyncio.to_thread(request.app.state.factory.delete_job, req.job_id)
    return {"status": "ok", "deleted": deleted}


@router.get("/get_jobs")
def get_jobs(request: Request):
    """Return all jobs as a dict: jobId -> job"""
    return request.app.state.factory.jobs


@router.get("/run_job")
async def run_job(job_id: str, request: Request):
    # Run job in thread to avoid blocking FastAPI
    await asyncio.to_thread(request.app.state.factory.run_job, job_id)
    return {"status": "ok"}


@router.get("/run_script")
async def run_script(path: str, request: Request):
    # Run job in thread to avoid blocking FastAPI
    await asyncio.to_thread(request.app.state.factory.run_script, path)
    return {"status": "ok"}
