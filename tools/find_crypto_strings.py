import re
import base64

with open('v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd', 'rb') as f:
    data = f.read()

# Look for base64 strings
b64_pattern = re.compile(rb'[A-Za-z0-9+/]{20,}={0,2}')
for m in b64_pattern.finditer(data):
    s = m.group(0)
    try:
        decoded = base64.b64decode(s)
        # Check if decoded is text
        if any(b in decoded for b in [b'http', b'script', b'google', b'vietqr', b'bank', b'api', b'key', b'token']):
            print("Decoded B64:", s[:30], "->", decoded[:100])
    except:
        pass

# Also look for any byte sequence containing "script.google.com" or "macros" or "apps"
for kw in [b'script.google.com', b'macros/s/', b'googleapis.com', b'vietqr', b'img.vietqr.io', b'api.vietqr.io', b't.me', b'telegram', b'discordapp']:
    pos = 0
    while True:
        pos = data.find(kw, pos)
        if pos == -1:
            break
        # print surrounding bytes
        start = max(0, pos - 40)
        end = min(len(data), pos + 100)
        print(f"Found keyword {kw} at {pos}: {data[start:end]}")
        pos += len(kw)

