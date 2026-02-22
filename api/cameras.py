# backend/machines/cameras.py
import cv2
import threading
import time
import sys
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/camera")

class CameraManager:
    def __init__(self, index: int):
        self.index = index
        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_frame: Optional[bytes] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.ref_count = 0 

    def _capture_loop(self):
        while not self.stop_event.is_set():
            if self.cap is None:
                break
            
            success, frame = self.cap.read()
            if success:
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                self.latest_frame = buffer.tobytes()
            else:
                # If read fails, the device might have timed out
                time.sleep(0.1)

    def start(self):
        with self.lock:
            if self.thread is None:
                # Use V4L2 for Pi to avoid backend conflicts
                backend = cv2.CAP_V4L2 if not sys.platform.startswith("win") else cv2.CAP_DSHOW
                self.cap = cv2.VideoCapture(self.index, backend)
                
                # --- THE SELECT() TIMEOUT FIX ---
                # 1. Force MJPEG (Compressed) to fit multiple cameras on the USB bus
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
                # 2. Reduce Resolution (Crucial for multi-camera stability)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                # 3. Buffer Settings (Linux Specific)
                # Setting this to 1 reduces latency and prevents stale frame timeouts
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not self.cap.isOpened():
                    raise RuntimeError(f"Hardware Error: Camera {self.index} busy or disconnected")

                self.stop_event.clear()
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
            self.ref_count += 1

    def stop(self):
        with self.lock:
            self.ref_count -= 1
            if self.ref_count <= 0:
                self.stop_event.set()
                if self.thread:
                    self.thread.join(timeout=1.0)
                if self.cap:
                    self.cap.release()
                self.cap = None
                self.thread = None
                self.ref_count = 0

camera_instances: Dict[str, CameraManager] = {}
global_lock = threading.Lock()

def get_or_create_manager(cam_id: str) -> CameraManager:
    with global_lock:
        if cam_id not in camera_instances:
            index = int(cam_id) if cam_id.isdigit() else cam_id
            camera_instances[cam_id] = CameraManager(index)
        return camera_instances[cam_id]

async def mjpeg_generator(cam_id: str):
    manager = get_or_create_manager(cam_id)
    manager.start()
    try:
        while not manager.stop_event.is_set():
            frame = manager.latest_frame
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            # This sleep ensures we don't saturate the CPU
            time.sleep(0.05) 
    finally:
        manager.stop()

@router.get("/detect")
def detect_cameras():
    available = []
    for i in range(5): # Limit scan to first 5
        cap = cv2.VideoCapture(i, cv2.CAP_V4L2 if not sys.platform.startswith("win") else cv2.CAP_DSHOW)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return {"available_indexes": available}

@router.get("/{cam_id}/stream")
def stream_camera(cam_id: str):
    return StreamingResponse(
        mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/{cam_id}/snapshot")
def snapshot(cam_id: str):
    manager = get_or_create_manager(cam_id)
    if not manager.thread:
        manager.start()
        time.sleep(0.5)
    
    frame = manager.latest_frame
    if not frame:
        raise HTTPException(status_code=500, detail="Frame Capture Timeout")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")
