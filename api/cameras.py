# backend/machines/cameras.py
import sys
import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict

router = APIRouter(prefix="/camera")

# persistent camera handles
cameras: Dict[str, cv2.VideoCapture] = {}

# map logical names → OpenCV indices
INDEX_MAP = {
    "board": 0,
    "liteplacer": 1,
}


def open_camera(index: int):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)  # Linux / Raspberry Pi default backend
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera index {index}")
    return cap


def get_camera(cam_id: str):
    if cam_id not in INDEX_MAP:
        raise HTTPException(404, f"Unknown camera '{cam_id}'")

    if cam_id not in cameras:
        cameras[cam_id] = open_camera(INDEX_MAP[cam_id])

    return cameras[cam_id]


def mjpeg_generator(cap: cv2.VideoCapture):
    while True:
        success, frame = cap.read()
        if not success:
            continue

        ret, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


# -------- Detect camera indices --------
@router.get("/detect")
def detect_cameras():
    available = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return {"available_indexes": available}


# -------- Start camera --------
@router.post("/{cam_id}/start")
def start_camera(cam_id: str):
    get_camera(cam_id)
    return {"status": "started", "camera": cam_id}


# -------- Stop camera --------
@router.post("/{cam_id}/stop")
def stop_camera(cam_id: str):
    if cam_id in cameras:
        cameras[cam_id].release()
        del cameras[cam_id]
    return {"status": "stopped", "camera": cam_id}


# -------- MJPEG stream --------
@router.get("/{cam_id}/stream")
def stream_camera(cam_id: str):
    cap = get_camera(cam_id)
    return StreamingResponse(
        mjpeg_generator(cap),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# -------- Snapshot --------
@router.get("/{cam_id}/snapshot")
def snapshot(cam_id: str):
    cap = get_camera(cam_id)
    success, frame = cap.read()
    if not success:
        raise HTTPException(500, "Failed to capture frame")

    _, buffer = cv2.imencode(".jpg", frame)
    return StreamingResponse(
        iter([buffer.tobytes()]),
        media_type="image/jpeg"
    )