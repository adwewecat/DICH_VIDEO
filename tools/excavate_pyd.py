import re
import json
from collections import defaultdict

def excavate():
    with open('v-translate-07-11/_internal/v_translate_07_11_core.cp310-win_amd64.pyd', 'rb') as f:
        data = f.read()

    # Find all strings (ASCII + UTF-8)
    # In Cython binaries, docstrings, method names, class names, and code strings are null-terminated UTF-8 / ASCII strings.
    raw_strings = []
    # Split on null bytes or extract printable runs
    parts = data.split(b'\x00')
    for p in parts:
        if len(p) >= 3:
            try:
                s = p.decode('utf-8')
                if any(c.isalnum() for c in s):
                    raw_strings.append(s)
            except:
                try:
                    s = p.decode('latin-1')
                    if any(c.isalnum() for c in s):
                        raw_strings.append(s)
                except:
                    pass

    print(f"Total raw strings extracted: {len(raw_strings)}")

    # Group into categories:
    classes = set()
    methods = defaultdict(list)
    docstrings = []
    ui_elements = []
    configs = []
    prompts = []
    urls = []

    class_pattern = re.compile(r'v_translate_07_11_core\.([A-Za-z0-9_]+)')
    method_pattern = re.compile(r'v_translate_07_11_core\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')

    for s in raw_strings:
        # Check URLs
        if 'http://' in s or 'https://' in s or 'api.' in s or 'www.' in s or '.com' in s:
            if len(s) < 200:
                urls.append(s)

        # Check classes & methods
        m = method_pattern.match(s)
        if m:
            cls, meth = m.groups()
            classes.add(cls)
            methods[cls].append(meth)
            continue
        c = class_pattern.match(s)
        if c:
            classes.add(c.group(1))
            continue

        # Check docstrings / long explanations
        if len(s) > 60 and any(keyword in s for keyword in ['translated', 'subtitle', 'audio', 'video', 'TTS', 'OCR', 'Gemini', 'CapCut', 'Bcut', 'Việt', 'tiếng', 'dịch', 'thực thi', 'lỗi', 'vse', 'ASR']):
            docstrings.append(s)

        # Check prompts
        if any(keyword in s.lower() for keyword in ['you are a', 'system prompt', 'instruction', 'translate the following', 'json format', 'gemini']):
            if len(s) > 40:
                prompts.append(s)

    print("\n================== CLASSES IDENTIFIED ==================")
    for cls in sorted(classes):
        print(f"Class: {cls} ({len(methods[cls])} methods)")
        for m in sorted(list(set(methods[cls])))[:10]:
            print(f"   - {m}")
        if len(methods[cls]) > 10:
            print(f"   ... and {len(methods[cls]) - 10} more methods")

    print("\n================== SAMPLE PROMPTS & PIPELINES ==================")
    for p in list(set(prompts))[:10]:
        print(f"Prompt / Instructions: {p[:180]}...\n")

    print("\n================== SAMPLE DOCSTRINGS & BUSINESS LOGIC ==================")
    for d in list(set(docstrings))[:15]:
        print(f"Doc/Logic: {d[:180]}...\n")

    # Write full excavation details to JSON
    out = {
        'classes': {cls: sorted(list(set(methods[cls]))) for cls in sorted(classes)},
        'prompts': sorted(list(set(prompts))),
        'docstrings': sorted(list(set(docstrings))),
        'urls': sorted(list(set(urls)))
    }
    with open('excavated_architecture.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Full structure saved to excavated_architecture.json")

if __name__ == '__main__':
    excavate()

