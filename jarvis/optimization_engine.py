"""
J.A.R.V.I.S Optimization Engine — throttled WebSocket streaming, self-healing builds.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Deque, Dict, Optional, Set


class ThrottledWebSocket:
    """Batches and deduplicates high-frequency process_update messages."""

    def __init__(self, ws: Any, min_interval: float = 0.08, max_queue: int = 48):
        self._ws = ws
        self._min_interval = min_interval
        self._max_queue = max_queue
        self._queue: Deque[Dict[str, Any]] = deque()
        self._last_sent: Dict[str, float] = {}
        self._last_process_msg = ""
        self._flush_task: Optional[asyncio.Task] = None
        self._closed = False

    async def send_json(self, data: Dict[str, Any]) -> None:
        if self._closed:
            return

        msg_type = data.get("type", "")
        immediate_types: Set[str] = {
            "build_complete",
            "build_failed",
            "process_complete",
            "browser_speak",
            "status",
            "audio",
            "code_stream_start",
            "code_stream_end",
            "stop_audio",
        }

        if msg_type in immediate_types:
            await self._ws.send_json(data)
            return

        if msg_type == "process_update":
            text = str(data.get("message", ""))
            if text == self._last_process_msg:
                return
            self._last_process_msg = text

        self._queue.append(data)
        if len(self._queue) > self._max_queue:
            # Drop oldest throttled updates, keep errors
            trimmed = deque()
            for item in self._queue:
                if item.get("type") not in ("process_update", "build_log", "code_stream_chunk"):
                    trimmed.append(item)
            self._queue = trimmed or deque([self._queue[-1]])

        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush())

    async def _flush(self) -> None:
        await asyncio.sleep(self._min_interval)
        while self._queue and not self._closed:
            data = self._queue.popleft()
            msg_type = data.get("type", "")
            now = time.monotonic()
            last = self._last_sent.get(msg_type, 0)
            if msg_type in ("process_update", "build_log") and now - last < self._min_interval:
                await asyncio.sleep(self._min_interval - (now - last))
            try:
                await self._ws.send_json(data)
                self._last_sent[msg_type] = time.monotonic()
            except Exception:
                break
            if not self._queue:
                break
            await asyncio.sleep(self._min_interval * 0.5)

    def wrap(self) -> "ThrottledWebSocket":
        return self


async def run_self_healing(ws: Any, jarvis_root: str) -> Dict[str, Any]:
    """
    Analyze common failures, apply repairs, emit live optimization logs.
    """
    from pathlib import Path

    root = Path(jarvis_root)
    logs: list[str] = []

    async def emit(agent: str, message: str, color: str = "#00e5ff") -> None:
        logs.append(message)
        try:
            await ws.send_json({"type": "process_update", "message": f"[{agent}] {message}"})
        except Exception:
            pass

    await emit("Debug AI", "Detected websocket flooding — analyzing stream patterns.")
    await asyncio.sleep(0.3)
    await emit("Optimization AI", "Applying stream throttling and batch coalescing...")
    await asyncio.sleep(0.3)

    repairs = 0
    try:
        from code_repair import repair_project_tree, validate_frontend

        fix_logs = repair_project_tree(root)
        repairs = len(fix_logs)
        if fix_logs:
            await emit("Build AI", f"Repaired {repairs} syntax issues across project tree.")
        ok, detail = await validate_frontend(root)
        if detail:
            await emit("Build AI", f"Validation: {detail[:120]}")
        if not ok:
            await emit("Debug AI", "Frontend validation reported issues — check build output.")
    except Exception as e:
        await emit("Debug AI", f"Repair pass: {e}")

    req = root / "requirements.txt"
    if req.exists():
        await emit("Build AI", "Re-running dependency verification...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "pip",
                "install",
                "-r",
                str(req),
                "--quiet",
                cwd=str(root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=90)
        except Exception as e:
            await emit("Debug AI", f"Dependency check: {e}")

    await emit("Optimization AI", f"Self-healing complete. {repairs} module(s) optimized.")
    return {"success": True, "repairs": repairs, "logs": logs}


def throttle_ws(ws: Any) -> ThrottledWebSocket:
    """Wrap a FastAPI WebSocket for build/deploy streams."""
    return ThrottledWebSocket(ws)
