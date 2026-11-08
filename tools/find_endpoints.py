import re

with open('v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd', 'rb') as f:
    data = f.read()

patterns = [
    rb'[a-zA-Z0-9_\-\.]{3,}\.(?:com|vn|net|org|io|dev|app|xyz|top|cc|me|online|site|ru|cn|live|pro)(?:/[^\x00\r\n\t "\'<>]+)?',
    rb'https?://[^\x00\r\n\t "\'<>]+',
    rb'AKfycb[a-zA-Z0-9\-_]{20,}',
    rb'vietqr[^\x00\r\n\t "\'<>]*',
    rb'api[^\x00\r\n\t "\'<>]*',
]

results = set()
for p in patterns:
    for m in re.finditer(p, data):
        try:
            s = m.group(0).decode('utf-8', errors='ignore')
            if len(s) > 5 and not s.startswith('.') and not s.endswith('.'):
                results.add(s)
        except:
            pass

found_list = sorted(list(results))
print(f"Total endpoints found: {len(found_list)}")
for r in found_list:
    # Print interesting items
    lower = r.lower()
    if any(k in lower for k in ['script', 'google', 'vietqr', 'akfy', 'api', 'proxy', 'auth', 'http', 'translate', 'license', 'sheet', 'drive', 'telegram', 'discord', 'server']):
        print(" ->", r)
