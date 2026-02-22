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
        self.ref_count = 0  # Track how many active streams are using this camera

    def _capture_loop(self):
        """Internal loop to continuously pull frames from hardware."""
        while not self.stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.1)
                continue
            
            success, frame = self.cap.read()
            if success:
                # Encode to JPEG for the MJPEG stream
                _, buffer = cv2.imencode(".jpg", frame)
                self.latest_frame = buffer.tobytes()
            else:
                # Small sleep to prevent high CPU usage on failed reads
                time.sleep(0.01)

    def start(self):
        with self.lock:
            if self.thread is None:
                # Use V4L2 for Linux/Pi; DSHOW for Windows
                backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_V4L2
                self.cap = cv2.VideoCapture(self.index, backend)
                
                # OPTIONAL: Lower resolution/FPS to save Pi bandwidth
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 20)

                if not self.cap.isOpened():
                    raise RuntimeError(f"Could not open camera {self.index}")

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

# Global storage for active camera managers
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
            # Cap the generator's output frequency
            time.sleep(0.04) # ~25 FPS
    finally:
        manager.stop()

# --- API Routes ---

@router.get("/detect")
def detect_cameras():
    available = []
    # Test first 10 indices
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return {"available_indexes": available}

@router.get("/{cam_id}/stream")
def stream_camera(cam_id: str):
    # This supports multiple tabs; each call starts a generator
    return StreamingResponse(
        mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/{cam_id}/snapshot")
def snapshot(cam_id: str):
    manager = get_or_create_manager(cam_id)
    # Ensure camera is running to take a snapshot
    if not manager.thread:
        manager.start()
        time.sleep(0.5) # Give it a moment to warm up
    
    frame = manager.latest_frame
    if not frame:
        raise HTTPException(status_code=500, detail="Camera frame not ready")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")
