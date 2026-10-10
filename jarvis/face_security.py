"""
JARVIS FACE RECOGNITION SECURITY SYSTEM
Real-time face detection, recognition, stranger detection, attention monitoring.
Uses OpenCV + face_recognition (dlib). Falls back gracefully if not installed.
"""
import os
import time
import asyncio
import base64
import json
from typing import Optional, Callable

# ── Graceful imports ──────────────────────────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

SECURITY_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "security")
os.makedirs(SECURITY_DATA_DIR, exist_ok=True)

KNOWN_FACES_FILE = os.path.join(SECURITY_DATA_DIR, "known_faces.json")


class FaceSecuritySystem:
    def __init__(self):
        self.is_running      = False
        self.is_authorized   = False
        self.stranger_alert  = False
        self.attention_level = 1.0   # 0.0 = not looking, 1.0 = fully attentive
        self.face_count      = 0
        self.last_frame_b64  = None
        self.last_scan_time  = 0.0

        self._known_encodings = []
        self._known_names     = []
        self._cap             = None
        self._task            = None
        self._callbacks: list[Callable] = []

        self._load_known_faces()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return CV2_AVAILABLE and FACE_REC_AVAILABLE and NP_AVAILABLE

    def start(self):
        if not self.is_available():
            print("[FaceSecurity] OpenCV/face_recognition not installed — security system offline.")
            return False
        if self.is_running:
            return True
        self.is_running = True
        self._task = asyncio.create_task(self._scan_loop())
        print("[FaceSecurity] Security system online.")
        return True

    def stop(self):
        self.is_running = False
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def enroll_user(self, name: str, image_b64: str) -> bool:
        """Enroll a new authorized user from a base64 image."""
        if not self.is_available():
            return False
        try:
            img_data = base64.b64decode(image_b64)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb)
            if not encodings:
                return False
            self._known_encodings.append(encodings[0].tolist())
            self._known_names.append(name)
            self._save_known_faces()
            print(f"[FaceSecurity] Enrolled: {name}")
            return True
        except Exception as e:
            print(f"[FaceSecurity] Enroll error: {e}")
            return False

    def get_status(self) -> dict:
        return {
            "available":      self.is_available(),
            "running":        self.is_running,
            "authorized":     self.is_authorized,
            "stranger_alert": self.stranger_alert,
            "attention":      round(self.attention_level, 2),
            "face_count":     self.face_count,
            "known_users":    self._known_names,
            "last_scan":      round(time.time() - self.last_scan_time, 1) if self.last_scan_time else None,
        }

    def on_event(self, callback: Callable):
        self._callbacks.append(callback)

    # ── Scan Loop ─────────────────────────────────────────────────────────────

    async def _scan_loop(self):
        """Async scan loop — runs face detection every 2 seconds."""
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                result = await loop.run_in_executor(None, self._scan_frame)
                if result:
                    self._fire_event(result)
            except Exception as e:
                print(f"[FaceSecurity] Scan error: {e}")
            await asyncio.sleep(2.0)

    def _scan_frame(self) -> Optional[dict]:
        """Synchronous frame capture and analysis (runs in thread pool)."""
        if not self._cap or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                return None

        ret, frame = self._cap.read()
        if not ret:
            return None

        self.last_scan_time = time.time()

        # Resize for speed
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # Detect faces
        face_locations = face_recognition.face_locations(rgb_small)
        self.face_count = len(face_locations)

        if not face_locations:
            self.attention_level = max(0.0, self.attention_level - 0.1)
            self.is_authorized = False
            return {"event": "no_face", "attention": self.attention_level}

        self.attention_level = min(1.0, self.attention_level + 0.2)

        # Recognize faces
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
        recognized_names = []
        stranger_detected = False

        for encoding in face_encodings:
            name = "Unknown"
            if self._known_encodings:
                known_np = np.array(self._known_encodings)
                matches = face_recognition.compare_faces(known_np, encoding, tolerance=0.55)
                distances = face_recognition.face_distance(known_np, encoding)
                if True in matches:
                    best_idx = np.argmin(distances)
                    if matches[best_idx]:
                        name = self._known_names[best_idx]
            recognized_names.append(name)
            if name == "Unknown":
                stranger_detected = True

        # Update state
        authorized_names = [n for n in recognized_names if n != "Unknown"]
        self.is_authorized = len(authorized_names) > 0
        prev_stranger = self.stranger_alert
        self.stranger_alert = stranger_detected

        # Encode frame thumbnail (small, for HUD)
        _, buf = cv2.imencode(".jpg", cv2.resize(frame, (160, 120)), [cv2.IMWRITE_JPEG_QUALITY, 60])
        self.last_frame_b64 = base64.b64encode(buf).decode()

        event_type = "authorized" if self.is_authorized else ("stranger" if stranger_detected else "face_detected")

        return {
            "event":      event_type,
            "names":      recognized_names,
            "authorized": self.is_authorized,
            "stranger":   stranger_detected,
            "new_stranger": stranger_detected and not prev_stranger,
            "face_count": self.face_count,
            "attention":  self.attention_level,
            "frame":      self.last_frame_b64,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_known_faces(self):
        if os.path.exists(KNOWN_FACES_FILE):
            try:
                with open(KNOWN_FACES_FILE) as f:
                    data = json.load(f)
                self._known_names     = data.get("names", [])
                self._known_encodings = data.get("encodings", [])
                print(f"[FaceSecurity] Loaded {len(self._known_names)} known faces.")
            except Exception:
                pass

    def _save_known_faces(self):
        try:
            with open(KNOWN_FACES_FILE, "w") as f:
                json.dump({"names": self._known_names, "encodings": self._known_encodings}, f)
        except Exception as e:
            print(f"[FaceSecurity] Save error: {e}")

    def _fire_event(self, event: dict):
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_system = FaceSecuritySystem()

def get_system() -> FaceSecuritySystem:
    return _system
