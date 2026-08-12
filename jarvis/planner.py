import json

class TaskPlanner:
    def __init__(self):
        self.active_task_type = None
        self.questions = []
        self.current_q_index = 0
        self.answers = {}

    def start_planning(self, request_text: str):
        bypass = ["just do it", "figure it out", "just go", "skip planning", "don't ask", "stop asking", "wing it", "surprise me", "do your thing"]
        for b in bypass:
            if b in request_text.lower():
                self.active_task_type = "build"
                self.answers = {"tech_stack": "React + Tailwind"}
                return True # bypass
        
        if "fix" in request_text.lower() or "error" in request_text.lower() or "bug" in request_text.lower():
            self.active_task_type = "fix"
            self.questions = [
                {"key": "project", "q": "Which project is this for?", "default": ""},
                {"key": "expected", "q": "What is the expected behavior?", "default": ""}
            ]
        elif "research" in request_text.lower() or "find out" in request_text.lower():
            self.active_task_type = "research"
            self.questions = [
                {"key": "depth", "q": "How deep should I go? A quick overview or comprehensive?", "default": "quick overview"},
                {"key": "format", "q": "Any specific output format?", "default": ""}
            ]
        elif "refactor" in request_text.lower() or "clean up" in request_text.lower():
            self.active_task_type = "refactor"
            self.questions = [
                {"key": "project", "q": "Which project are we refactoring?", "default": ""},
                {"key": "goal", "q": "Is the main goal readability, performance, or something else?", "default": "readability"}
            ]
        else:
            self.active_task_type = "build"
            self.questions = [
                {"key": "project", "q": "What project name shall we use?", "default": ""},
                {"key": "tech_stack", "q": "Any preferred tech stack? Default is React and Tailwind.", "default": "React and Tailwind"}
            ]
        return False

    def process_answer(self, text: str):
        if self.current_q_index < len(self.questions):
            q_key = self.questions[self.current_q_index]["key"]
            self.answers[q_key] = text
            self.current_q_index += 1
        
        if self.current_q_index < len(self.questions):
            return self.questions[self.current_q_index]["q"]
        return None # done planning

    def handle_confirmation(self, text: str):
        if text.lower() in ['yes', 'yeah', 'yep', 'go', 'do it']:
            return True
        return False

    def build_prompt(self, original_request: str) -> str:
        prompt = f"Task: {original_request}\\n"
        prompt += "Details:\\n"
        for k, v in self.answers.items():
            prompt += f"- {k.capitalize()}: {v}\\n"
        if self.active_task_type == "build" and "tech_stack" not in self.answers:
            prompt += "- Tech Stack: React + Tailwind\\n"
        return prompt
