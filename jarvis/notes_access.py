import asyncio

async def _run_applescript(script: str, timeout: int = 20):
    try:
        try:
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except FileNotFoundError:
            return ""
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode().strip()
    except Exception as e:
        return ""

async def get_recent_notes(count: int = 10):
    script = f'''
tell application "Notes"
    set output to ""
    set allNotes to notes of default account
    set noteCount to count of allNotes
    if noteCount > {count} then set noteCount to {count}
    repeat with i from 1 to noteCount
        set n to item i of allNotes
        set t to name of n
        set d to creation date of n
        set f to name of container of n
        set output to output & t & "|||" & d & "|||" & f & linefeed
    end repeat
    return output
end tell
    '''
    res = await _run_applescript(script)
    notes = []
    if res:
        for line in res.split('\\n'):
            if '|||' in line:
                parts = line.split('|||')
                notes.append({"title": parts[0], "date": parts[1], "folder": parts[2]})
    return notes

async def read_note(title_match: str):
    title_match = title_match.replace('"', '\\"')
    script = f'''
tell application "Notes"
    set allNotes to notes of default account whose name contains "{title_match}"
    if (count of allNotes) > 0 then
        set n to item 1 of allNotes
        set t to name of n
        set b to body of n
        return t & "|||" & b
    end if
    return ""
end tell
    '''
    res = await _run_applescript(script)
    if '|||' in res:
        parts = res.split('|||', 1)
        return {"title": parts[0], "body": parts[1][:3000] if len(parts) > 1 else ""}
    return None

async def search_notes_apple(query: str, count: int = 5):
    query = query.replace('"', '\\"')
    script = f'''
tell application "Notes"
    set output to ""
    set allNotes to notes of default account whose body contains "{query}" or name contains "{query}"
    set noteCount to count of allNotes
    if noteCount > {count} then set noteCount to {count}
    repeat with i from 1 to noteCount
        set n to item i of allNotes
        set t to name of n
        set d to creation date of n
        set output to output & t & "|||" & d & linefeed
    end repeat
    return output
end tell
    '''
    res = await _run_applescript(script)
    notes = []
    if res:
        for line in res.split('\\n'):
            if '|||' in line:
                parts = line.split('|||')
                notes.append({"title": parts[0], "date": parts[1]})
    return notes

def _body_to_html(body: str) -> str:
    lines = body.split('\\n')
    html_lines = []
    for line in lines:
        if not line.strip():
            html_lines.append("<br>")
        elif line.startswith("- [ ] "):
            html_lines.append(f"<div><input type='checkbox'> {line[6:]}</div>")
        elif line.startswith("- "):
            html_lines.append(f"<ul><li>{line[2:]}</li></ul>")
        elif line.startswith("# "):
            html_lines.append(f"<h2>{line[2:]}</h2>")
        else:
            html_lines.append(f"<div>{line}</div>")
    return "\\n".join(html_lines)

async def create_apple_note(title: str, body: str, folder: str = "Notes"):
    title = title.replace('"', '\\"')
    html_body = _body_to_html(body).replace('"', '\\"')
    script = f'''
tell application "Notes"
    tell account "iCloud"
        if not (exists folder "{folder}") then
            make new folder with properties {{name:"{folder}"}}
        end if
        make new note at folder "{folder}" with properties {{name:"{title}", body:"<h1>{title}</h1>" & "{html_body}"}}
    end tell
end tell
    '''
    res = await _run_applescript(script)
    return True

async def get_note_folders():
    script = '''
tell application "Notes"
    set output to ""
    repeat with f in folders of default account
        set output to output & (name of f) & linefeed
    end repeat
    return output
end tell
    '''
    res = await _run_applescript(script)
    return [line.strip() for line in res.split('\\n') if line.strip()]
