# backend/machines/cameras.py
import sys
import cv2
import threading
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict

router = APIRouter(prefix="/camera")

# persistent camera handles and latest frames
cameras: Dict[str, cv2.VideoCapture] = {}
latest_frame: Dict[str, bytes] = {}
camera_threads: Dict[str, threading.Thread] = {}
stop_flags: Dict[str, threading.Event] = {}



def open_camera(index: int):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)  # Linux / Raspberry Pi
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera index {index}")
    return cap


def camera_loop(cam_id: str):
    cap = cameras[cam_id]
    stop_event = stop_flags[cam_id]

    while not stop_event.is_set():
        success, frame = cap.read()
        if success:
            _, buffer = cv2.imencode(".jpg", frame)
            latest_frame[cam_id] = buffer.tobytes()
        else:
            time.sleep(0.01)  # prevent busy loop


def get_camera(cam_id: str):
    if cam_id not in cameras:
        # Convert string id to int if it's a digit (e.g., "0" -> 0)
        index = int(cam_id) if cam_id.isdigit() else cam_id
        cameras[cam_id] = open_camera(index)
        stop_flags[cam_id] = threading.Event()
        thread = threading.Thread(target=camera_loop, args=(cam_id,), daemon=True)
        camera_threads[cam_id] = thread
        thread.start()

    return cameras[cam_id]


def mjpeg_generator(cam_id: str):
    while True:
        frame = latest_frame.get(cam_id)
        if not frame:
            time.sleep(0.01)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
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
        stop_flags[cam_id].set()
        camera_threads[cam_id].join(timeout=1)
        cameras[cam_id].release()
        del cameras[cam_id]
        del camera_threads[cam_id]
        del stop_flags[cam_id]
        if cam_id in latest_frame:
            del latest_frame[cam_id]
    return {"status": "stopped", "camera": cam_id}


# -------- MJPEG stream --------
@router.get("/{cam_id}/stream")
def stream_camera(cam_id: str):
    get_camera(cam_id)
    return StreamingResponse(
        mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# -------- Snapshot --------
@router.get("/{cam_id}/snapshot")
def snapshot(cam_id: str):
    get_camera(cam_id)
    frame = latest_frame.get(cam_id)
    if not frame:
        raise HTTPException(500, "No frame available yet")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")