from pathlib import Path
p = Path('templates.py')
p.write_text(p.read_text(encoding='utf-8').replace('\\"\\"\\"', '"""'), encoding='utf-8')
