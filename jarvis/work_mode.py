import json
import os
import asyncio

class WorkSession:
    def __init__(self):
        self.working_dir = ""
        self.project_name = ""
        self.message_count = 0
        self.process = None

    async def start(self, working_dir: str, project_name: str):
        self.working_dir = working_dir
        self.project_name = project_name
        self.message_count = 0
        self.save()

    async def send(self, user_text: str):
        cmd = ["claude", "-p", "--output-format", "text", "--dangerously-skip-permissions"]
        if self.message_count > 0:
            cmd.append("--continue")
        
        self.message_count += 1
        self.save()
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=user_text.encode()), timeout=300)
        return stdout.decode().strip()

    def stop(self):
        self.working_dir = ""
        self.project_name = ""
        self.message_count = 0
        self.save()

    def save(self):
        with open('data/active_session.json', 'w') as f:
            json.dump({
                "working_dir": self.working_dir,
                "project_name": self.project_name,
                "message_count": self.message_count
            }, f)

    def restore(self) -> bool:
        if os.path.exists('data/active_session.json'):
            try:
                with open('data/active_session.json', 'r') as f:
                    data = json.load(f)
                self.working_dir = data.get("working_dir", "")
                self.project_name = data.get("project_name", "")
                self.message_count = data.get("message_count", 0)
                return bool(self.working_dir)
            except:
                pass
        return False

def is_casual_question(text: str) -> bool:
    text = text.lower().strip()
    casual_words = ["hello", "hi", "hey", "how are you", "what time", "weather", "thanks", "ok", "got it"]
    if len(text.split()) < 5 and any(w in text for w in casual_words):
        return True
    return False
