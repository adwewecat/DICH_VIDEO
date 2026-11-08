with open('v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd', 'rb') as f:
    data = f.read()

# Search for substrings like "license", "lease", "wallet", "proxy", "hwid"
keywords = [
    b'_verify_license', b'_LicenseAccountState', b'_FeatureLease',
    b'set_security_locked', b'_LicenseDialog', b'_poll_balance_loop'
]

for kw in keywords:
    pos = 0
    print(f"\n================ KEYWORD: {kw} ================")
    while True:
        pos = data.find(kw, pos)
        if pos == -1:
            break
        start = max(0, pos - 200)
        end = min(len(data), pos + 300)
        # Extract readable strings from chunk
        chunk = data[start:end]
        import string
        readable = ''.join([chr(b) if chr(b) in string.printable else '.' for b in chunk])
        print(f"[{pos}]: {readable}\n")
        pos += len(kw)
