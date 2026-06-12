with open('builder.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the bad f-string on line 528
old = 'f"netstat -ano | findstr LISTENING | findstr ":{port} ""'
new = 'f"netstat -ano | findstr LISTENING | findstr :{port}"'

if old in code:
    code = code.replace(old, new, 1)
    print("OK: Fixed netstat f-string")
else:
    print("SKIP: pattern not found")

with open('builder.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Done.")
