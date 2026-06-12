import asyncio
import os

CALENDAR_ACCOUNTS = os.getenv("CALENDAR_ACCOUNTS", "").split(",")
_calendar_cache = []

async def _ensure_calendar_running():
    script = 'tell application "System Events" to if not (exists process "Calendar") then tell application "Calendar" to activate'
    try:
        proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
        await proc.wait()
    except FileNotFoundError:
        return
    await asyncio.sleep(2)

def _parse_applescript_date(s: str):
    return s

async def _fetch_calendar_events(cal_name: str, timeout: int = 12):
    script = f'''
tell application "Calendar"
    set cal to calendar "{cal_name}"
    set dateList to start date of every event of cal
    set summaryList to summary of every event of cal
    set allDayList to allday event of every event of cal
    set output to ""
    repeat with i from 1 to count of dateList
        set output to output & ((item i of dateList) as string) & "|||" & (item i of summaryList) & "|||" & (item i of allDayList) & linefeed
    end repeat
    return output
end tell
    '''
    try:
        try:
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except FileNotFoundError:
            return []
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        events = []
        for line in stdout.decode().strip().split('\\n'):
            if '|||' in line:
                parts = line.split('|||')
                if len(parts) >= 3:
                    events.append({
                        "calendar": cal_name,
                        "title": parts[1],
                        "start": parts[0],
                        "start_dt": parts[0],
                        "all_day": "true" in parts[2].lower()
                    })
        return events
    except Exception as e:
        return []

async def refresh_cache():
    global _calendar_cache
    await _ensure_calendar_running()
    all_events = []
    accounts = [a for a in CALENDAR_ACCOUNTS if a]
    for i in range(0, len(accounts), 2):
        batch = accounts[i:i+2]
        tasks = [_fetch_calendar_events(cal) for cal in batch]
        results = await asyncio.gather(*tasks)
        for res in results:
            all_events.extend(res)
    # sort all-day first
    all_events.sort(key=lambda x: (not x['all_day'], x['start_dt']))
    _calendar_cache = all_events

async def get_todays_events():
    global _calendar_cache
    if not _calendar_cache:
        await refresh_cache()
    return _calendar_cache

async def get_upcoming_events(hours: int = 4):
    events = await get_todays_events()
    return [e for e in events if not e['all_day']]

def format_events_for_context(events):
    if not events:
        return "No events today."
    return "\\n".join([f"- {e['title']} at {e['start']}" for e in events])

def format_schedule_summary(events):
    if not events:
        return "Your schedule is clear today, sir."
    return f"You have {len(events)} events today."
