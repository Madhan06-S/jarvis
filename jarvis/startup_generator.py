import os
import json
import asyncio
import builder
from ai_brain import call_ai

async def generate_startup(idea_or_domain: str, ws=None):
    if ws:
        await ws.send_json({"type": "process_update", "message": "INITIALIZING AUTONOMOUS STARTUP GENERATOR..."})
        await ws.send_json({"type": "process_update", "message": f"Analyzing market domain: {idea_or_domain}"})
        
    prompt = f"""You are an elite Silicon Valley AI Founder. The user wants to build a startup in this domain/idea: '{idea_or_domain}'.
Your job is to invent a complete, billion-dollar startup concept.
Return a RAW JSON object (no markdown, no backticks) with these keys:
- "name": The futuristic name of the startup (1-2 words).
- "tagline": A highly cinematic 3-7 word tagline.
- "brand_color": A hex code for the primary brand color.
- "pitch": A 2-sentence elevator pitch.
- "features": An array of 3 killer features.
- "build_instruction": A very detailed instruction string that will be sent to an AI Architect to build the actual React/FastAPI product. This must describe the exact 3D cinematic aesthetic, the pages needed, and the specific UI elements.
"""

    if ws:
        await ws.send_json({"type": "process_update", "message": "Consulting AI Founder models..."})
        
    try:
        response = await call_ai("You are an elite Silicon Valley AI Founder.", prompt, max_tokens=1000)
        # Clean JSON
        import re
        json_str = re.sub(r'```json|```', '', response).strip()
        data = json.loads(json_str)
    except Exception as e:
        if ws:
            await ws.send_json({"type": "process_update", "message": f"Founder AI failed to parse JSON: {str(e)}. Using fallback."})
        data = {
            "name": "Nexus " + idea_or_domain.title(),
            "tagline": "The future of " + idea_or_domain,
            "brand_color": "#00ffcc",
            "pitch": "We are revolutionizing the space.",
            "features": ["AI Integration", "3D Visualization", "Realtime Data"],
            "build_instruction": f"Build a cinematic web application for {idea_or_domain}. Make it look extremely premium, futuristic, and use 3D effects."
        }

    startup_name = data.get("name", "UnknownStartup")
    if ws:
        await ws.send_json({"type": "process_update", "message": f"🚀 FOUNDRY SUCCESS: Incubating '{startup_name}'"})
        await ws.send_json({"type": "process_update", "message": f"TAGLINE: {data.get('tagline')}"})
    
    # Write pitch deck
    project_dir = os.path.join(os.path.expanduser("~"), "jarvis-projects", startup_name.lower().replace(" ", "-"))
    os.makedirs(project_dir, exist_ok=True)
    
    deck = f"""# {startup_name.upper()}
> {data.get("tagline")}

## Elevator Pitch
{data.get("pitch")}

## Brand Identity
**Primary Color:** {data.get("brand_color")}

## Core Features
"""
    for f in data.get("features", []):
        deck += f"- {f}\n"
        
    with open(os.path.join(project_dir, "PITCH_DECK.md"), "w", encoding="utf-8") as f:
        f.write(deck)
        
    if ws:
        await ws.send_json({"type": "process_update", "message": "Pitch deck generated and saved to workspace."})
        await ws.send_json({"type": "process_update", "message": "Handing off blueprint to Architecture AI..."})
        
    # Trigger the builder!
    build_prompt = f"Startup Name: {startup_name}. Brand Color: {data.get('brand_color')}. Tagline: {data.get('tagline')}. {data.get('build_instruction')} MAKE IT EXTREMELY CINEMATIC AND 3D."
    
    res = await builder.build_fullstack_project(build_prompt, ws)
    
    if res.get("status") == "ok":
        return {"success": True, "startup_name": startup_name, "url": res.get("url")}
    else:
        return {"success": False, "error": res.get("error")}
