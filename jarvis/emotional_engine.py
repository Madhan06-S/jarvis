"""
JARVIS EMOTIONAL AI ENGINE
Detects emotional state from: typing speed, time of day, voice tone keywords,
system usage patterns, interaction behavior.
Adapts: UI palette, voice tone, response style, animations.
"""
import time
import math
import json
import asyncio
from typing import Optional
from collections import deque

# ── Emotional States ──────────────────────────────────────────────────────────
EMOTIONS = {
    "focused":   {"color": "#00BFFF", "accent": "#0077aa", "energy": 0.8},
    "calm":      {"color": "#00e5a0", "accent": "#007755", "energy": 0.4},
    "stressed":  {"color": "#ff6600", "accent": "#cc3300", "energy": 1.2},
    "excited":   {"color": "#ffcc00", "accent": "#ff8800", "energy": 1.5},
    "tired":     {"color": "#6688aa", "accent": "#334455", "energy": 0.3},
    "angry":     {"color": "#ff2200", "accent": "#880000", "energy": 1.8},
    "anxious":   {"color": "#cc44ff", "accent": "#660099", "energy": 1.1},
    "neutral":   {"color": "#00BFFF", "accent": "#0055aa", "energy": 0.7},
}

# Stress keywords in voice/text
STRESS_WORDS    = {"urgent", "asap", "immediately", "broken", "error", "failed", "crash", "fix", "help", "problem", "issue", "wrong", "bad", "terrible"}
EXCITED_WORDS   = {"amazing", "awesome", "great", "perfect", "love", "incredible", "fantastic", "yes", "launch", "build", "create", "new"}
TIRED_WORDS     = {"tired", "sleep", "rest", "exhausted", "slow", "later", "tomorrow", "break", "pause"}
ANGRY_WORDS     = {"stupid", "useless", "hate", "terrible", "worst", "garbage", "trash", "idiot", "broken"}
ANXIOUS_WORDS   = {"worried", "nervous", "anxious", "scared", "afraid", "uncertain", "maybe", "not sure", "confused"}


class EmotionalEngine:
    def __init__(self):
        self.current_emotion = "neutral"
        self.emotion_score   = 0.0
        self.confidence      = 0.5

        # Typing speed tracking
        self._keystroke_times: deque = deque(maxlen=20)
        self._last_keystroke  = 0.0
        self._avg_wpm         = 0.0

        # Interaction history
        self._message_lengths: deque = deque(maxlen=10)
        self._response_times:  deque = deque(maxlen=10)
        self._last_interaction = time.time()

        # Emotion history for smoothing
        self._emotion_history: deque = deque(maxlen=5)

        # Callbacks
        self._on_change_callbacks = []

    # ── Public API ────────────────────────────────────────────────────────────

    def record_keystroke(self):
        """Call this on every keypress in the chat input."""
        now = time.time()
        if self._last_keystroke > 0:
            gap = now - self._last_keystroke
            if 0.02 < gap < 3.0:  # filter out pauses and held keys
                self._keystroke_times.append(gap)
        self._last_keystroke = now

    def analyze_text(self, text: str) -> str:
        """Analyze text content for emotional signals. Returns detected emotion."""
        words = set(text.lower().split())
        self._message_lengths.append(len(text))

        scores = {
            "stressed":  len(words & STRESS_WORDS)  * 2.0,
            "excited":   len(words & EXCITED_WORDS) * 1.5,
            "tired":     len(words & TIRED_WORDS)   * 1.8,
            "angry":     len(words & ANGRY_WORDS)   * 2.5,
            "anxious":   len(words & ANXIOUS_WORDS) * 1.6,
        }

        # Typing speed signal
        wpm = self._calc_wpm()
        if wpm > 80:
            scores["stressed"]  = scores.get("stressed", 0) + 1.5
            scores["excited"]   = scores.get("excited",  0) + 1.0
        elif wpm < 25 and wpm > 0:
            scores["tired"]     = scores.get("tired",    0) + 1.5

        # Message length signal
        if len(text) > 200:
            scores["stressed"]  = scores.get("stressed", 0) + 0.5
        elif len(text) < 10:
            scores["tired"]     = scores.get("tired",    0) + 0.5

        # Time of day signal
        hour = time.localtime().tm_hour
        if 0 <= hour < 6:
            scores["tired"]     = scores.get("tired",    0) + 2.0
        elif 22 <= hour < 24:
            scores["tired"]     = scores.get("tired",    0) + 1.0
        elif 9 <= hour < 12 or 14 <= hour < 17:
            scores["focused"]   = scores.get("focused",  0) + 1.0

        # Punctuation signals
        if text.count("!") >= 2:
            scores["excited"]   = scores.get("excited",  0) + 1.0
        if text.count("?") >= 2:
            scores["anxious"]   = scores.get("anxious",  0) + 0.8
        if text.isupper() and len(text) > 5:
            scores["angry"]     = scores.get("angry",    0) + 1.5

        # Pick dominant emotion
        if not scores or max(scores.values()) < 0.5:
            detected = "neutral"
        else:
            detected = max(scores, key=scores.get)

        # Smooth with history
        self._emotion_history.append(detected)
        smoothed = self._smooth_emotion()

        if smoothed != self.current_emotion:
            self.current_emotion = smoothed
            self._fire_change(smoothed)

        return smoothed

    def get_state(self) -> dict:
        """Return full emotional state for frontend."""
        emotion_data = EMOTIONS.get(self.current_emotion, EMOTIONS["neutral"])
        wpm = self._calc_wpm()
        hour = time.localtime().tm_hour

        return {
            "emotion":    self.current_emotion,
            "color":      emotion_data["color"],
            "accent":     emotion_data["accent"],
            "energy":     emotion_data["energy"],
            "wpm":        round(wpm, 1),
            "hour":       hour,
            "confidence": round(self.confidence, 2),
            "history":    list(self._emotion_history),
        }

    def get_voice_modifier(self) -> dict:
        """Return TTS voice modifiers based on emotion."""
        modifiers = {
            "focused":  {"stability": 0.55, "style": 0.3,  "rate": 1.0},
            "calm":     {"stability": 0.70, "style": 0.15, "rate": 0.9},
            "stressed": {"stability": 0.35, "style": 0.5,  "rate": 1.15},
            "excited":  {"stability": 0.40, "style": 0.65, "rate": 1.1},
            "tired":    {"stability": 0.75, "style": 0.1,  "rate": 0.85},
            "angry":    {"stability": 0.30, "style": 0.7,  "rate": 1.2},
            "anxious":  {"stability": 0.45, "style": 0.45, "rate": 1.05},
            "neutral":  {"stability": 0.50, "style": 0.3,  "rate": 1.0},
        }
        return modifiers.get(self.current_emotion, modifiers["neutral"])

    def get_response_prefix(self) -> str:
        """Get emotion-aware response prefix for JARVIS."""
        prefixes = {
            "stressed":  "Sir, I'm detecting elevated stress. ",
            "tired":     "You seem tired, sir. ",
            "excited":   "",
            "angry":     "Sir, I'd recommend a brief pause. ",
            "anxious":   "",
            "focused":   "",
            "calm":      "",
            "neutral":   "",
        }
        return prefixes.get(self.current_emotion, "")

    def on_change(self, callback):
        """Register callback for emotion changes."""
        self._on_change_callbacks.append(callback)

    # ── Private ───────────────────────────────────────────────────────────────

    def _calc_wpm(self) -> float:
        if len(self._keystroke_times) < 3:
            return 0.0
        avg_gap = sum(self._keystroke_times) / len(self._keystroke_times)
        if avg_gap <= 0:
            return 0.0
        # Average word = 5 chars, gap in seconds per char
        wpm = (1.0 / avg_gap) * 60 / 5
        self._avg_wpm = wpm
        return min(wpm, 200)

    def _smooth_emotion(self) -> str:
        if not self._emotion_history:
            return "neutral"
        # Majority vote from recent history
        counts = {}
        for e in self._emotion_history:
            counts[e] = counts.get(e, 0) + 1
        winner = max(counts, key=counts.get)
        self.confidence = counts[winner] / len(self._emotion_history)
        return winner

    def _fire_change(self, emotion: str):
        for cb in self._on_change_callbacks:
            try:
                cb(emotion, self.get_state())
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_engine = EmotionalEngine()

def get_engine() -> EmotionalEngine:
    return _engine

def analyze(text: str) -> str:
    return _engine.analyze_text(text)

def get_state() -> dict:
    return _engine.get_state()

def get_voice_modifier() -> dict:
    return _engine.get_voice_modifier()

def get_response_prefix() -> str:
    return _engine.get_response_prefix()
