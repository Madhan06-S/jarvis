import sys
import re

with open('builder.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('async def generate_project_files('):
        start_idx = i
    elif start_idx != -1 and line.startswith('    base_files["README.md"] = f"#'):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_func = '''async def generate_project_files(plan: dict, original_description: str, ws=None) -> Dict[str, str]:
    """Generate flawless complete professional files using Pollinations AI"""
    plan["stack"] = "react_fastapi"
    await _ws_log(ws, "⚡ Brainstorming perfect file structure and pro-level UI...")
    
    base_files = templates.get_react_fastapi_files(plan)
    
    system_prompt = f"""You are a master full-stack web developer and UI/UX designer.
Your task is to build a PRO-LEVEL, stunning, premium web application for: {plan.get('title', 'Project')}
Description: {original_description}

Rules:
1. You MUST use React (Vite) + Tailwind CSS + Lucide React for frontend.
2. The UI MUST be jaw-dropping: use beautiful dark themes, glassmorphism (bg-white/10 backdrop-blur), vibrant gradients, hover micro-interactions, and highly professional layouts. Do NOT make it basic.
3. You MUST output the code in markdown blocks with the filename specified in the language tag. Example:
```tsx filename="frontend/src/App.tsx"
// code...
```
"""

    user_prompt = f"""Generate the COMPLETE code for a premium, multi-page application.
Include a stunning Landing Page, Home Page, buttons, and multiple sections.
Provide the full files for 'frontend/src/App.tsx', 'frontend/src/index.css', and 'backend/main.py'.
DO NOT USE JSON. DO NOT EXPLAIN.
"""
    await _ws_log(ws, "⚡ Coding premium dynamic codebase via AI (this takes a moment)...")
    try:
        import re
        raw = await _call_claude(system_prompt, user_prompt, max_tokens=15000)
        
        # Parse markdown blocks with filenames
        pattern = r'```[a-zA-Z0-9_-]*\s+filename="([^"]+)"\\n(.*?)```'
        matches = re.findall(pattern, raw, re.DOTALL)
        
        if not matches:
            alt_pattern = r'```[a-zA-Z0-9_-]*\\n(?://|#)\s*([a-zA-Z0-9_/-]+\.[a-zA-Z0-9]+)\\n(.*?)```'
            matches = re.findall(alt_pattern, raw, re.DOTALL)
            
        if not matches:
            raise ValueError("Could not find any code blocks with filenames in the AI response.")
            
        for filepath, content in matches:
            base_files[filepath] = content.strip()
            
        await _ws_log(ws, f"✓ AI successfully generated {len(matches)} premium files!")
            
    except Exception as e:
        import traceback
        print(f"AI Gen Error: {traceback.format_exc()}")
        await _ws_log(ws, f"⚠ AI code generation failed, using standard template. ({str(e)[:50]})")

'''
    with open('builder.py', 'w', encoding='utf-8') as f:
        f.writelines(lines[:start_idx])
        f.write(new_func)
        f.writelines(lines[end_idx:])
    print('SUCCESS')
else:
    print('FAILED TO FIND BLOCK')
