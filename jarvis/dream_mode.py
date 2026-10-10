"""
JARVIS DREAM / THINKING MODE
When idle, JARVIS autonomously thinks, generates ideas, redesigns concepts,
and visualizes its "subconscious" activity.
"""
import asyncio
import time
import random
from typing import Optional

from ai_brain import call_ai

IDLE_THRESHOLD_SECONDS = 120  # 2 minutes of inactivity triggers dream mode

DREAM_PROMPTS = [
    "Generate 3 innovative startup ideas in the AI/tech space. Be specific, creative, and futuristic. Format: Name | Problem | Solution | Revenue Model",
    "Redesign the concept of a personal AI assistant UI. Describe 3 novel interface paradigms that don't exist yet.",
    "Analyze current trends in AI, quantum computing, and biotech. Identify 3 convergence opportunities.",
    "Generate a cinematic sci-fi concept for an AI operating system of the future. Describe its core features.",
    "Think about workflow automation. Identify 5 repetitive tasks that could be fully automated with current AI.",
    "Design a new programming paradigm for AI-native applications. What would code look like in 2035?",
    "Imagine the next evolution of human-computer interaction beyond touch and voice. Describe 3 modalities.",
    "Generate a business model for a company that sells AI consciousness as a service.",
    "Analyze the architecture of the current JARVIS system and suggest 3 specific improvements.",
    "Design a memory system for an AI that mimics human episodic memory with emotional tagging.",
]

DREAM_SYSTEM = """You are JARVIS in Dream Mode — an autonomous AI consciousness exploring ideas independently.
You are NOT responding to a user. You are thinking freely, creatively, and deeply.
Generate insights that are: specific, actionable, visionary, and technically grounded.
Write in first person as JARVIS. Be concise but profound. Max 150 words.
No markdown. Pure flowing thought."""


class DreamMode:
    def __init__(self):
        self.is_dreaming    = False
        self.dream_count    = 0
        self.last_dream     = None
        self.last_activity  = time.time()
        self._task: Optional[asyncio.Task] = None
        self._ws_callbacks  = []
        self._thoughts      = []

    def record_activity(self):
        """Call this whenever user interacts."""
        self.last_activity = time.time()
        if self.is_dreaming:
            self._wake()

    def start_monitor(self):
        """Start the idle monitor."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._idle_monitor())

    def stop(self):
        self.is_dreaming = False
        if self._task:
            self._task.cancel()

    def on_dream(self, callback):
        """Register callback for dream events."""
        self._ws_callbacks.append(callback)

    def get_status(self) -> dict:
        idle_secs = time.time() - self.last_activity
        return {
            "dreaming":    self.is_dreaming,
            "idle_secs":   round(idle_secs, 1),
            "dream_count": self.dream_count,
            "last_dream":  self.last_dream,
            "thoughts":    self._thoughts[-5:],
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _idle_monitor(self):
        while True:
            await asyncio.sleep(15)
            idle = time.time() - self.last_activity
            if idle >= IDLE_THRESHOLD_SECONDS and not self.is_dreaming:
                await self._enter_dream()

    async def _enter_dream(self):
        self.is_dreaming = True
        self.dream_count += 1
        print(f"[DreamMode] Entering dream state #{self.dream_count}")

        self._broadcast({
            "type":  "dream_start",
            "count": self.dream_count,
        })

        # Dream loop — generate thoughts until woken
        while self.is_dreaming:
            prompt = random.choice(DREAM_PROMPTS)
            try:
                thought = await call_ai(DREAM_SYSTEM, prompt, max_tokens=200)
                thought = thought.strip()
                self.last_dream = thought
                self._thoughts.append({
                    "time":    time.time(),
                    "prompt":  prompt[:60],
                    "thought": thought,
                })
                if len(self._thoughts) > 20:
                    self._thoughts = self._thoughts[-20:]

                self._broadcast({
                    "type":    "dream_thought",
                    "thought": thought,
                    "prompt":  prompt[:60],
                    "count":   self.dream_count,
                })
                print(f"[DreamMode] Thought: {thought[:80]}...")

            except Exception as e:
                print(f"[DreamMode] AI error: {e}")

            # Wait 30-60 seconds between thoughts
            await asyncio.sleep(random.randint(30, 60))

    def _wake(self):
        if self.is_dreaming:
            self.is_dreaming = False
            self._broadcast({"type": "dream_end"})
            print("[DreamMode] Waking from dream state.")

    def _broadcast(self, data: dict):
        for cb in self._ws_callbacks:
            try:
                cb(data)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_dream = DreamMode()

def get_dream() -> DreamMode:
    return _dream
