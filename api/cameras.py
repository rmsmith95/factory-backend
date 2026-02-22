# backend/machines/cameras.py
import cv2
import threading
import time
import sys
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

# Setup logging to see hardware transitions in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info(f"Starting hardware capture thread for camera {self.index}")
        while not self.stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                break
            
            success, frame = self.cap.read()
            if success:
                # Compression is KEY to avoiding select() timeouts on Pi
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                self.latest_frame = buffer.tobytes()
            else:
                logger.warning(f"Failed to read frame from camera {self.index}")
                time.sleep(0.1)
        logger.info(f"Capture thread for camera {self.index} exited.")

    def start(self):
        with self.lock:
            self.ref_count += 1
            if self.thread is None:
                logger.info(f"Opening hardware: Camera {self.index}")
                # Use V4L2 for Pi/Linux; DSHOW for Windows
                backend = cv2.CAP_V4L2 if not sys.platform.startswith("win") else cv2.CAP_DSHOW
                self.cap = cv2.VideoCapture(self.index, backend)
                
                # FORCE MJPEG: This is the #1 fix for multi-camera select() timeouts
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Minimise lag

                if not self.cap.isOpened():
                    self.ref_count -= 1
                    raise RuntimeError(f"Camera {self.index} is busy or unavailable.")

                self.stop_event.clear()
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()

    def stop(self):
        with self.lock:
            self.ref_count -= 1
            if self.ref_count <= 0:
                logger.info(f"Closing hardware: Camera {self.index}")
                self.stop_event.set()
                if self.thread:
                    self.thread.join(timeout=2.0)
                if self.cap:
                    self.cap.release()
                self.cap = None
                self.thread = None
                self.ref_count = 0
                # Crucial: Give the Pi kernel a moment to actually free the device
                time.sleep(0.2)

# Singleton-style storage
camera_instances: Dict[str, CameraManager] = {}
global_lock = threading.Lock()

def get_manager(cam_id: str) -> CameraManager:
    with global_lock:
        if cam_id not in camera_instances:
            index = int(cam_id) if cam_id.isdigit() else cam_id
            camera_instances[cam_id] = CameraManager(index)
        return camera_instances[cam_id]

async def mjpeg_generator(cam_id: str):
    manager = get_manager(cam_id)
    manager.start()
    try:
        while True:
            frame = manager.latest_frame
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            
            # This sleep controls the stream FPS in the browser
            await asyncio.sleep(0.04) # ~25 FPS
            
            # Check if camera was externally stopped
            if manager.stop_event.is_set():
                break
    except Exception as e:
        logger.error(f"Stream error on {cam_id}: {e}")
    finally:
        manager.stop()

# Support for the async sleep in generator
import asyncio

@router.get("/detect")
def detect_cameras():
    available = []
    # Only scan if not currently streaming to avoid interrupting active feeds
    for i in range(4):
        backend = cv2.CAP_V4L2 if not sys.platform.startswith("win") else cv2.CAP_DSHOW
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return {"available_indexes": available}

@router.get("/{cam_id}/stream")
async def stream_camera(cam_id: str):
    return StreamingResponse(
        mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/{cam_id}/snapshot")
async def snapshot(cam_id: str):
    manager = get_manager(cam_id)
    manager.start()
    # Wait briefly for first frame if just started
    for _ in range(10):
        if manager.latest_frame: break
        await asyncio.sleep(0.1)
    
    frame = manager.latest_frame
    manager.stop() # Release ref count
    
    if not frame:
        raise HTTPException(status_code=500, detail="Hardware Timeout")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")
