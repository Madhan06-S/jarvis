"""
JARVIS System Status Skill — Real-time System Telemetry (psutil)
"""
import psutil
from datetime import datetime
from typing import Dict, Any

NAME = "System Status"
DESCRIPTION = "Real-time system diagnostics (CPU, RAM, Battery, Disk, Time & Date)"
TRIGGERS = ["system status", "cpu usage", "ram usage", "battery", "status report", "system info", "time", "date", "clock"]

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    now = datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%A, %B %d, %Y")

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    battery_info = "N/A"
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            battery_info = f"{bat.percent}% ({'Plugged in' if bat.power_plugged else 'Discharging'})"

    if "time" in t and not "status" in t:
        return {
            "handled": True,
            "spoken_response": f"The current time is {time_str}, sir.",
            "hud_card": None
        }

    if "date" in t and not "status" in t:
        return {
            "handled": True,
            "spoken_response": f"Today is {date_str}.",
            "hud_card": None
        }

    spoken = f"System online. CPU usage is {cpu:.0f} percent, RAM is at {mem.percent:.0f} percent, disk space is {disk.percent:.0f} percent full."

    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "system_status",
            "title": "STARK SYSTEM TELEMETRY",
            "data": {
                "time": time_str,
                "date": date_str,
                "cpu": f"{cpu:.1f}%",
                "ram": f"{mem.percent:.1f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)",
                "disk": f"{disk.percent:.1f}%",
                "battery": battery_info
            }
        }
    }
