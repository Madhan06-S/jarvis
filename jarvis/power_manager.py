"""
JARVIS AI POWER MANAGEMENT SYSTEM
Monitors CPU, GPU, battery, thermal conditions.
Autonomously optimizes processes and adjusts performance.
"""
import time
import asyncio
import os
import platform
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

IS_WINDOWS = platform.system() == "Windows"


class PowerManager:
    def __init__(self):
        self.is_running      = False
        self.power_mode      = "balanced"   # eco | balanced | performance | turbo
        self.cpu_percent     = 0.0
        self.ram_percent     = 0.0
        self.battery_percent = None
        self.is_charging     = None
        self.temp_celsius    = None
        self.gpu_percent     = 0.0
        self.optimization_log = []
        self._task: Optional[asyncio.Task] = None
        self._callbacks = []
        self._high_cpu_streak = 0
        self._low_cpu_streak  = 0

    def is_available(self) -> bool:
        return PSUTIL_AVAILABLE

    def start(self):
        if not self.is_available():
            return False
        if self.is_running:
            return True
        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("[PowerManager] AI power management online.")
        return True

    def stop(self):
        self.is_running = False

    def on_event(self, callback):
        self._callbacks.append(callback)

    def get_status(self) -> dict:
        return {
            "available":     self.is_available(),
            "running":       self.is_running,
            "power_mode":    self.power_mode,
            "cpu":           round(self.cpu_percent, 1),
            "ram":           round(self.ram_percent, 1),
            "battery":       self.battery_percent,
            "charging":      self.is_charging,
            "temp":          self.temp_celsius,
            "gpu":           round(self.gpu_percent, 1),
            "recent_actions": self.optimization_log[-5:],
        }

    def set_mode(self, mode: str):
        """Manually set power mode."""
        valid = {"eco", "balanced", "performance", "turbo"}
        if mode in valid:
            self.power_mode = mode
            self._apply_mode(mode)
            return True
        return False

    # ── Monitor Loop ──────────────────────────────────────────────────────────

    async def _monitor_loop(self):
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                await loop.run_in_executor(None, self._collect_stats)
                self._auto_optimize()
            except Exception as e:
                print(f"[PowerManager] Error: {e}")
            await asyncio.sleep(3.0)

    def _collect_stats(self):
        """Collect system stats synchronously."""
        self.cpu_percent = psutil.cpu_percent(interval=1)
        self.ram_percent = psutil.virtual_memory().percent

        # Battery
        bat = psutil.sensors_battery()
        if bat:
            self.battery_percent = round(bat.percent, 1)
            self.is_charging     = bat.power_plugged

        # Temperature (Linux/Mac only, Windows needs WMI)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                all_temps = []
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            all_temps.append(entry.current)
                if all_temps:
                    self.temp_celsius = round(max(all_temps), 1)
        except Exception:
            # Simulate temp from CPU load on Windows
            self.temp_celsius = round(35 + self.cpu_percent * 0.45, 1)

        # GPU (try nvidia-smi on Windows)
        if IS_WINDOWS:
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    self.gpu_percent = float(result.stdout.strip())
            except Exception:
                self.gpu_percent = 0.0

    def _auto_optimize(self):
        """Automatically adjust power mode based on conditions."""
        actions = []

        # High CPU streak detection
        if self.cpu_percent > 85:
            self._high_cpu_streak += 1
            self._low_cpu_streak = 0
        elif self.cpu_percent < 30:
            self._low_cpu_streak += 1
            self._high_cpu_streak = 0
        else:
            self._high_cpu_streak = max(0, self._high_cpu_streak - 1)
            self._low_cpu_streak  = max(0, self._low_cpu_streak  - 1)

        # Auto-switch modes
        if self._high_cpu_streak >= 3 and self.power_mode not in ("eco",):
            if self.battery_percent and self.battery_percent < 20 and not self.is_charging:
                if self.power_mode != "eco":
                    self.power_mode = "eco"
                    actions.append("Switched to ECO mode — battery critical.")
                    self._apply_mode("eco")
            elif self.temp_celsius and self.temp_celsius > 85:
                if self.power_mode != "balanced":
                    self.power_mode = "balanced"
                    actions.append(f"Thermal throttle — CPU at {self.temp_celsius}°C.")
                    self._apply_mode("balanced")

        elif self._low_cpu_streak >= 5 and self.power_mode == "performance":
            self.power_mode = "balanced"
            actions.append("Downscaled to BALANCED — low activity detected.")

        # Battery warnings
        if self.battery_percent is not None:
            if self.battery_percent < 10 and not self.is_charging:
                actions.append(f"CRITICAL: Battery at {self.battery_percent}%. Connect charger immediately.")
            elif self.battery_percent < 20 and not self.is_charging:
                actions.append(f"Battery low: {self.battery_percent}%.")

        for action in actions:
            self.optimization_log.append({"time": time.time(), "action": action})
            if len(self.optimization_log) > 20:
                self.optimization_log = self.optimization_log[-20:]
            self._fire({"type": "optimization", "action": action, "mode": self.power_mode})

    def _apply_mode(self, mode: str):
        """Apply OS-level power settings."""
        if IS_WINDOWS:
            plans = {
                "eco":         "a1841308-3541-4fab-bc81-f71556f20b4a",  # Power saver
                "balanced":    "381b4222-f694-41f0-9685-ff5bb260df2e",  # Balanced
                "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",  # High performance
                "turbo":       "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",  # High performance
            }
            guid = plans.get(mode)
            if guid:
                try:
                    import subprocess
                    subprocess.run(["powercfg", "/setactive", guid],
                                   capture_output=True, timeout=3)
                except Exception:
                    pass

    def _fire(self, event: dict):
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_manager = PowerManager()

def get_manager() -> PowerManager:
    return _manager
