import re
import json
import string
from collections import defaultdict

def extract_strings(file_path, min_len=4):
    with open(file_path, 'rb') as f:
        data = f.read()

    # ASCII strings
    ascii_re = re.compile(b'[ -~]{' + str(min_len).encode() + b',}')
    ascii_strings = [s.decode('ascii', errors='ignore') for s in ascii_re.findall(data)]

    # UTF-16 strings
    utf16_re = re.compile(b'(?:[\x20-\x7e]\x00){' + str(min_len).encode() + b',}')
    utf16_strings = [s.decode('utf-16le', errors='ignore') for s in utf16_re.findall(data)]

    return set(ascii_strings + utf16_strings)

def analyze():
    pyd_path = 'v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd'
    print(f'Analyzing {pyd_path}...')
    all_strings = extract_strings(pyd_path, min_len=4)
    print(f'Total extracted strings: {len(all_strings)}')

    # 1. Search for URLs & IPs
    urls = []
    ips = []
    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    url_pattern = re.compile(r'https?://[^\s<>"\']+|wss?://[^\s<>"\']+')

    for s in all_strings:
        found_urls = url_pattern.findall(s)
        for u in found_urls:
            urls.append(u)
        found_ips = ip_pattern.findall(s)
        for ip in found_ips:
            if not ip.startswith('0.') and not ip.startswith('127.') and not ip.startswith('255.'):
                ips.append(ip)

    urls = sorted(list(set(urls)))
    ips = sorted(list(set(ips)))

    print('\n=== FOUND URLS ===')
    for u in urls:
        print('  -', u)

    print('\n=== FOUND NON-LOCAL IPS ===')
    for ip in ips:
        print('  -', ip)

    # 2. Search for Cython symbols and functions
    cython_funcs = [s for s in all_strings if s.startswith('__pyx_')]
    print(f'\n=== CYTHON SYMBOLS ({len(cython_funcs)} found) ===')
    # Filter module names and function names
    funcs = [s for s in cython_funcs if 'func_' in s or 'meth_' in s or 'f_' in s or 'cfunc_' in s]
    modules = set()
    for s in cython_funcs:
        if 'v_translate' in s or 'core' in s or 'dubbing' in s or 'subtitle' in s:
            modules.add(s)

    print(f'Sample Cython symbols: {list(cython_funcs)[:25]}')

    # 3. Search for suspicious keywords
    suspicious_terms = [
        'webhook', 'discord', 'telegram', 'token', 'stealer', 'grabber',
        'keylogger', 'backdoor', 'trojan', 'inject', 'payload', 'rat',
        'powershell', 'cmd.exe', 'reg add', 'reg delete', 'hkey',
        'appdata', 'roaming', 'temp', 'download', 'upload', 'telemetry',
        'analytics', 'track', 'license', 'expire', 'auth', 'verify', 'hwid',
        'uuid', 'machine_id', 'crypto', 'wallet', 'passwords', 'cookie'
    ]

    suspicious_matches = defaultdict(list)
    for s in all_strings:
        lower = s.lower()
        for term in suspicious_terms:
            if term in lower:
                # exclude very common false positives
                if len(s) < 150:
                    suspicious_matches[term].append(s)

    print('\n=== SUSPICIOUS KEYWORDS BREAKDOWN ===')
    for term, matches in suspicious_matches.items():
        sample = list(set(matches))[:10]
        print(f"[{term}] ({len(matches)} occurrences):")
        for m in sample:
            print(f"    * {m}")

    # Save summary report
    report = {
        'urls': urls,
        'ips': ips,
        'cython_symbols_count': len(cython_funcs),
        'suspicious_terms': {k: list(set(v)) for k, v in suspicious_matches.items()}
    }
    with open('binary_audit_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print('\nReport written to binary_audit_report.json')

if __name__ == '__main__':
    analyze()

