with open('templates.py','r',encoding='utf-8') as f: code=f.read()
if 'from fallback_templates import' not in code:
    code = 'from fallback_templates import get_fallback_app\n' + code
    print('OK: import added')
else:
    print('SKIP: already imported')
# expose get_fallback_app on the module
if 'get_fallback_app' not in code.split('from fallback_templates')[1][:20]:
    pass  # it's imported at top, accessible as templates.get_fallback_app
with open('templates.py','w',encoding='utf-8') as f: f.write(code)
print('Done')
