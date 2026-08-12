with open('templates.py','r',encoding='utf-8') as f: code=f.read()
# Replace old import with new one that chains education
code = code.replace(
    'from fallback_templates import get_fallback_app',
    'from fallback_education import get_fallback_app'
)
with open('templates.py','w',encoding='utf-8') as f: f.write(code)
print('OK: templates.py updated')

# Now deploy to current project
import sys, os
sys.path.insert(0,'d:/ironnn/jarvis')
from fallback_education import get_fallback_app
fb = get_fallback_app('education','School Portal')
base = r'C:\Users\nandh\jarvis-projects\school-website'
app_path = os.path.join(base,'frontend','src','App.tsx')
be_path  = os.path.join(base,'backend','main.py')
if os.path.exists(app_path):
    with open(app_path,'w',encoding='utf-8') as f: f.write(fb['app'])
    print('App.tsx written')
if os.path.exists(be_path):
    with open(be_path,'w',encoding='utf-8') as f: f.write(fb['backend'])
    print('main.py written')
print('DONE')
