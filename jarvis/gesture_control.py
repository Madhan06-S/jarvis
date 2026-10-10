"""
JARVIS HOLOGRAPHIC GESTURE CONTROL
MediaPipe Hands — detects swipe, pinch, point, fist gestures.
Sends gesture events to frontend via WebSocket.
"""
import time
import asyncio
import math
from typing import Optional, Callable

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False


# ── Gesture Definitions ───────────────────────────────────────────────────────
GESTURES = {
    "swipe_left":   "PANEL_PREV",
    "swipe_right":  "PANEL_NEXT",
    "swipe_up":     "SCROLL_UP",
    "swipe_down":   "SCROLL_DOWN",
    "pinch":        "ZOOM_IN",
    "spread":       "ZOOM_OUT",
    "point":        "SELECT",
    "fist":         "CLOSE",
    "open_hand":    "OPEN",
    "thumbs_up":    "CONFIRM",
    "peace":        "SCREENSHOT",
}


class GestureController:
    def __init__(self):
        self.is_running   = False
        self.last_gesture = None
        self.gesture_time = 0.0
        self._callbacks: list[Callable] = []
        self._task = None

        # Tracking state
        self._prev_wrist_x = None
        self._prev_wrist_y = None
        self._swipe_start  = None
        self._swipe_start_time = 0.0

    def is_available(self) -> bool:
        return CV2_AVAILABLE and MP_AVAILABLE and NP_AVAILABLE

    def start(self):
        if not self.is_available():
            print("[Gesture] MediaPipe not installed — gesture control offline.")
            return False
        if self.is_running:
            return True
        self.is_running = True
        self._task = asyncio.create_task(self._gesture_loop())
        print("[Gesture] Holographic gesture control online.")
        return True

    def stop(self):
        self.is_running = False

    def on_gesture(self, callback: Callable):
        self._callbacks.append(callback)

    def get_status(self) -> dict:
        return {
            "available":    self.is_available(),
            "running":      self.is_running,
            "last_gesture": self.last_gesture,
            "last_time":    round(time.time() - self.gesture_time, 1) if self.gesture_time else None,
        }

    # ── Gesture Loop ──────────────────────────────────────────────────────────

    async def _gesture_loop(self):
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                gesture = await loop.run_in_executor(None, self._detect_gesture)
                if gesture:
                    self._fire(gesture)
            except Exception as e:
                print(f"[Gesture] Error: {e}")
            await asyncio.sleep(0.1)  # 10fps gesture detection

    def _detect_gesture(self) -> Optional[dict]:
        """Single frame gesture detection."""
        mp_hands = mp.solutions.hands
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        with mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.7
        ) as hands:
            results = hands.process(rgb)

        if not results.multi_hand_landmarks:
            self._prev_wrist_x = None
            self._prev_wrist_y = None
            return None

        lm = results.multi_hand_landmarks[0].landmark

        # Key landmarks
        wrist     = lm[0]
        thumb_tip = lm[4]
        index_tip = lm[8]
        middle_tip= lm[12]
        ring_tip  = lm[16]
        pinky_tip = lm[20]

        # Finger extension detection
        def is_extended(tip_idx, pip_idx):
            return lm[tip_idx].y < lm[pip_idx].y

        index_ext  = is_extended(8,  6)
        middle_ext = is_extended(12, 10)
        ring_ext   = is_extended(16, 14)
        pinky_ext  = is_extended(20, 18)
        thumb_ext  = lm[4].x < lm[3].x  # rough thumb check

        fingers_up = sum([index_ext, middle_ext, ring_ext, pinky_ext])

        # Pinch detection (thumb + index close)
        pinch_dist = math.sqrt(
            (thumb_tip.x - index_tip.x)**2 +
            (thumb_tip.y - index_tip.y)**2
        )

        gesture_name = None

        # Classify gesture
        if pinch_dist < 0.05:
            gesture_name = "pinch"
        elif fingers_up == 0 and not thumb_ext:
            gesture_name = "fist"
        elif fingers_up == 4 and thumb_ext:
            gesture_name = "open_hand"
        elif index_ext and not middle_ext and not ring_ext and not pinky_ext:
            gesture_name = "point"
        elif index_ext and middle_ext and not ring_ext and not pinky_ext:
            gesture_name = "peace"
        elif thumb_ext and not index_ext and not middle_ext:
            gesture_name = "thumbs_up"
        elif fingers_up >= 3 and pinch_dist > 0.15:
            gesture_name = "spread"

        # Swipe detection via wrist movement
        wx, wy = wrist.x, wrist.y
        if self._prev_wrist_x is not None:
            dx = wx - self._prev_wrist_x
            dy = wy - self._prev_wrist_y
            speed = math.sqrt(dx**2 + dy**2)

            if speed > 0.08:  # fast movement threshold
                if abs(dx) > abs(dy):
                    gesture_name = "swipe_right" if dx > 0 else "swipe_left"
                else:
                    gesture_name = "swipe_down" if dy > 0 else "swipe_up"

        self._prev_wrist_x = wx
        self._prev_wrist_y = wy

        if not gesture_name:
            return None

        # Debounce — don't fire same gesture twice within 0.8s
        now = time.time()
        if gesture_name == self.last_gesture and now - self.gesture_time < 0.8:
            return None

        self.last_gesture = gesture_name
        self.gesture_time = now

        action = GESTURES.get(gesture_name, "UNKNOWN")
        return {
            "gesture": gesture_name,
            "action":  action,
            "wrist_x": round(wx, 3),
            "wrist_y": round(wy, 3),
            "fingers": fingers_up,
        }

    def _fire(self, gesture: dict):
        for cb in self._callbacks:
            try:
                cb(gesture)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_controller = GestureController()

def get_controller() -> GestureController:
    return _controller
