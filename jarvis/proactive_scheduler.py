"""
JARVIS Proactive Scheduler Engine — APScheduler with SQLite Persistence
"""
import os
import time
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

scheduler = AsyncIOScheduler()
_initialized = False
_websocket_ref = None

def init_proactive_scheduler():
    global scheduler, _initialized
    if _initialized:
        return
    
    os.makedirs("data", exist_ok=True)
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///data/scheduler.db')
    }
    scheduler.configure(jobstores=jobstores)
    scheduler.start()
    _initialized = True
    print("[Proactive Scheduler] APScheduler online with SQLite persistence.")

def set_websocket_reference(ws):
    global _websocket_ref
    _websocket_ref = ws

async def send_mobile_push_notification(message: str, title: str = "JARVIS Alert"):
    """
    Sends push notification to user's phone via ntfy.sh (No API key needed).
    Topic: jarvis_stark_alerts
    """
    topic = os.getenv("NTFY_TOPIC", "jarvis_stark_alerts")
    url = f"https://ntfy.sh/{topic}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                data=message.encode('utf-8'),
                headers={
                    "Title": title,
                    "Priority": "high",
                    "Tags": "robot,bell"
                }
            )
            print(f"[Mobile Push] Notification sent to ntfy.sh/{topic}: {message}")
    except Exception as e:
        print(f"[Mobile Push Error] {e}")

async def run_scheduled_briefing():
    """Triggered by APScheduler for daily briefings."""
    from skills import weather_skill, system_status_skill
    print("[Proactive Scheduler] Running daily briefing job...")
    
    w_res = await weather_skill.run("weather in Mumbai")
    sys_res = await system_status_skill.run("system status")
    
    briefing_text = f"Good morning sir! Daily briefing: {w_res['spoken_response']} {sys_res['spoken_response']}"
    await send_mobile_push_notification(briefing_text, title="JARVIS Daily Briefing")

def schedule_daily_briefing(hour: int = 8, minute: int = 0):
    job_id = "daily_briefing_job"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    scheduler.add_job(
        run_scheduled_briefing,
        'cron',
        hour=hour,
        minute=minute,
        id=job_id,
        replace_existing=True
    )
    print(f"[Proactive Scheduler] Daily briefing scheduled for {hour:02d}:{minute:02d}.")

def schedule_one_shot_reminder(message: str, run_at_ts: float):
    job_id = f"reminder_{int(run_at_ts)}"
    
    async def _remind_job():
        text = f"Reminder: {message}"
        print(f"[Proactive Scheduler] {text}")
        await send_mobile_push_notification(text, title="JARVIS Reminder")
        
    scheduler.add_job(
        _remind_job,
        'date',
        run_date=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(run_at_ts)),
        id=job_id,
        replace_existing=True
    )
