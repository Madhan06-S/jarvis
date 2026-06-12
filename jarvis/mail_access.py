import asyncio
import re

async def _ensure_mail_running():
    script = 'tell application "System Events" to if not (exists process "Mail") then tell application "Mail" to activate'
    try:
        proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
        await proc.wait()
    except FileNotFoundError:
        pass

async def _run_mail_script(script: str, timeout: int = 20):
    try:
        try:
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except FileNotFoundError:
            return ""
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode().strip()
    except Exception as e:
        return ""

def _short_sender(sender: str) -> str:
    match = re.search(r'^(.*?)\s*<', sender)
    return match.group(1).strip() if match else sender.strip()

async def get_unread_count():
    await _ensure_mail_running()
    script = '''
tell application "Mail"
    set totalCount to 0
    set output to ""
    repeat with acc in accounts
        set accName to name of acc
        set unreadCount to unread count of mailbox "INBOX" of acc
        set totalCount to totalCount + unreadCount
        set output to output & accName & "|||" & unreadCount & linefeed
    end repeat
    return (totalCount as string) & linefeed & "---" & linefeed & output
end tell
    '''
    res = await _run_mail_script(script)
    if not res:
        return {"total": 0, "accounts": {}}
    parts = res.split("---")
    total = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
    accounts = {}
    if len(parts) > 1:
        for line in parts[1].strip().split('\\n'):
            if '|||' in line:
                name, count = line.split('|||')
                accounts[name.strip()] = int(count.strip())
    return {"total": total, "accounts": accounts}

async def get_recent_messages(count: int = 10):
    await _ensure_mail_running()
    script = f'''
tell application "Mail"
    set output to ""
    set msgs to messages of inbox whose date received is greater than ((current date) - 7 * days)
    set msgCount to count of msgs
    if msgCount > {count} then set msgCount to {count}
    repeat with i from 1 to msgCount
        set msg to item i of msgs
        set sender string to sender of msg
        set subj to subject of msg
        set isRead to read status of msg
        set d to date received of msg
        set preview to content of msg
        set preview to characters 1 thru 150 of preview as string
        set output to output & sender string & "|||" & subj & "|||" & d & "|||" & isRead & "|||" & preview & linefeed
    end repeat
    return output
end tell
    '''
    res = await _run_mail_script(script)
    messages = []
    if res:
        for line in res.split('\\n'):
            if '|||' in line:
                parts = line.split('|||')
                if len(parts) >= 5:
                    messages.append({
                        "sender": parts[0],
                        "subject": parts[1],
                        "date": parts[2],
                        "read": "true" in parts[3].lower(),
                        "preview": parts[4]
                    })
    return messages

async def get_unread_messages(count: int = 10):
    messages = await get_recent_messages(count=50)
    return [m for m in messages if not m['read']][:count]

async def search_mail(query: str, count: int = 10):
    query = query.replace('"', '\\"')
    script = f'''
tell application "Mail"
    set output to ""
    set msgs to (messages of inbox whose subject contains "{query}" or sender contains "{query}")
    set msgCount to count of msgs
    if msgCount > {count} then set msgCount to {count}
    repeat with i from 1 to msgCount
        set msg to item i of msgs
        set sender string to sender of msg
        set subj to subject of msg
        set d to date received of msg
        set output to output & sender string & "|||" & subj & "|||" & d & linefeed
    end repeat
    return output
end tell
    '''
    res = await _run_mail_script(script)
    messages = []
    if res:
        for line in res.split('\\n'):
            if '|||' in line:
                parts = line.split('|||')
                messages.append({"sender": parts[0], "subject": parts[1], "date": parts[2]})
    return messages

async def read_message(subject_match: str):
    subject_match = subject_match.replace('"', '\\"')
    script = f'''
tell application "Mail"
    set msgs to (messages of inbox whose subject contains "{subject_match}")
    if (count of msgs) > 0 then
        set msg to item 1 of msgs
        set sender string to sender of msg
        set subj to subject of msg
        set d to date received of msg
        set c to content of msg
        return sender string & "|||" & subj & "|||" & d & "|||" & c
    end if
    return ""
end tell
    '''
    res = await _run_mail_script(script)
    if '|||' in res:
        parts = res.split('|||', 3)
        return {
            "sender": parts[0],
            "subject": parts[1],
            "date": parts[2],
            "content": parts[3][:3000] if len(parts) > 3 else ""
        }
    return None

def format_unread_summary(unread_data: dict) -> str:
    total = unread_data.get("total", 0)
    if total == 0:
        return "Inbox is clear, sir."
    accts = unread_data.get("accounts", {})
    details = ", ".join([f"{k} {v}" for k, v in accts.items() if v > 0])
    return f"You have {total} unread messages: {details}."

def format_messages_for_voice(messages: list) -> str:
    if not messages:
        return "No messages."
    m = messages[0]
    return f"One message from {_short_sender(m['sender'])}: {m['subject']}."
