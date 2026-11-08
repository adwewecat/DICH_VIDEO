import re

with open('v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd', 'rb') as f:
    data = f.read()

# Search for system prompt chunks
keywords = [
    b'system_instruction', b'D\xe1\xbb\x8bch sang ti\xe1\xba\xbfng Vi\xe1\xbb\x87t',
    b'ph\xe1\xbb\xa5 \xc4\x91\xe1\xbb\x81', b'subtitle', b'gemini-2.0',
    b'gemini-1.5', b'temperature', b'top_p', b'google.genai'
]

matches = []
for kw in keywords:
    pos = 0
    while True:
        pos = data.find(kw, pos)
        if pos == -1:
            break
        start = max(0, pos - 150)
        end = min(len(data), pos + 350)
        chunk = data[start:end]
        try:
            decoded = chunk.decode('utf-8', errors='ignore')
            matches.append((pos, decoded))
        except:
            pass
        pos += len(kw)

for pos, text in matches[:25]:
    # Clean up non-printable
    import string
    printable = ''.join(c if (c in string.printable or ord(c) > 127) else ' ' for c in text)
    print(f"[{pos}]: {printable}\n---")
