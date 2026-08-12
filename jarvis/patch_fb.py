with open('builder.py','r',encoding='utf-8') as f: code=f.read()
old = "        await _ws_log(ws, f\"\u26a0 AI failed ({str(e)[:60]}), stub files will load. Try rebuilding.\")"
new = "        await _ws_log(ws, f\"\u26a0 AI failed ({str(e)[:60]}) -- using built-in domain template.\")\n        fb = templates.get_fallback_app(domain, plan.get('title','App'))\n        base_files['frontend/src/App.tsx'] = fb['app']\n        base_files['backend/main.py'] = fb['backend']"
if old in code:
    code=code.replace(old,new); print('PATCHED')
else:
    print('SEARCH FAILED')
    print(repr(code[code.find('stub files'):code.find('stub files')+100]))
with open('builder.py','w',encoding='utf-8') as f: f.write(code)
