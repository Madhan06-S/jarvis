import re

with open('builder.py', 'r', encoding='utf-8') as f:
    code = f.read()

stream_func = (
    "\nasync def _stream_live_code(ws, text: str):\n"
    "    if not ws: return\n"
    "    try:\n"
    "        await ws.send_json({'type': 'code_stream_start'})\n"
    "        chunk_size = 50\n"
    "        for i in range(0, len(text), chunk_size):\n"
    "            chunk = text[i:i+chunk_size]\n"
    "            await ws.send_json({'type': 'code_stream_chunk', 'text': chunk})\n"
    "            await asyncio.sleep(0.01)\n"
    "        await ws.send_json({'type': 'code_stream_end'})\n"
    "    except Exception:\n"
    "        pass\n"
    "\n"
)

anchor = "async def _ws_log(ws, line: str):"
if anchor in code and "_stream_live_code" not in code:
    code = code.replace(anchor, stream_func + anchor)
    print("OK: Inserted _stream_live_code function")
else:
    print("SKIP: _stream_live_code already present or anchor not found")

old_call = "raw = await _call_claude(system_prompt, user_prompt, max_tokens=15000)"
new_call = ("raw = await _call_claude(system_prompt, user_prompt, max_tokens=15000)\n"
            "        await _stream_live_code(ws, raw)")

if old_call in code:
    code = code.replace(old_call, new_call, 1)
    print("OK: Added streaming call in generate_project_files")
else:
    print("SKIP: Anchor not found for generate_project_files")

old_mod = "raw = await _call_claude(system, user_prompt, max_tokens=15000)"
new_mod = ("raw = await _call_claude(system, user_prompt, max_tokens=15000)\n"
           "        await _stream_live_code(ws, raw)")

count = code.count(old_mod)
if count > 0:
    code = code.replace(old_mod, new_mod)
    print(f"OK: Added streaming call in modify_project ({count} location(s))")
else:
    print("SKIP: Anchor not found for modify_project")

with open('builder.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Done.")
