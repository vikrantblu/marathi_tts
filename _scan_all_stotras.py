"""Scan all stotra/data text files across all platforms for wrong-script characters."""
import sys, io, os, re, unicodedata, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

_BASE = os.path.dirname(os.path.abspath(__file__))

ROOTS = [
    os.path.join(_BASE, 'marathi_tts_web', 'data', 'stotras'),
    os.path.join(_BASE, 'marathi_tts_desktop', 'stotras'),
    os.path.join(_BASE, 'marathi_tts_mobile', 'app', 'src', 'main', 'assets', 'stotras'),
    os.path.join(_BASE, 'stotras'),
]

# Bengali: U+0980–U+09FF
# Gujarati: U+0A80–U+0AFF
# Gurmukhi: U+0A00–U+0A7F
# Telugu: U+0C00–U+0C7F
# Tamil: U+0B80–U+0BFF
# Kannada: U+0C80–U+0CFF
# Malayalam: U+0D00–U+0D7F
WRONG_SCRIPT_RANGES = [
    (0x0980, 0x09FF, 'Bengali'),
    (0x0A00, 0x0A7F, 'Gurmukhi'),
    (0x0A80, 0x0AFF, 'Gujarati'),
    (0x0B00, 0x0B7F, 'Oriya'),
    (0x0B80, 0x0BFF, 'Tamil'),
    (0x0C00, 0x0C7F, 'Telugu'),
    (0x0C80, 0x0CFF, 'Kannada'),
    (0x0D00, 0x0D7F, 'Malayalam'),
    (0x200B, 0x200F, 'ZeroWidth'),
    (0x200C, 0x200C, 'ZWNJ'),
    (0x200D, 0x200D, 'ZWJ'),
]

def classify(cp):
    for lo, hi, name in WRONG_SCRIPT_RANGES:
        if lo <= cp <= hi:
            return name
    return None

total_issues = 0
for root in ROOTS:
    for fpath in sorted(glob.glob(os.path.join(root, '*.txt'))):
        fname = os.path.relpath(fpath, _BASE)
        try:
            with open(fpath, encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f'ERROR reading {fname}: {e}')
            continue
        file_issues = []
        for i, line in enumerate(lines, 1):
            for j, ch in enumerate(line):
                cp = ord(ch)
                script = classify(cp)
                if script:
                    file_issues.append((i, j, ch, hex(cp), script, line.rstrip()))
        if file_issues:
            print(f'\n=== {fname} ({len(file_issues)} issues) ===')
            for li, pos, ch, cph, script, ln in file_issues:
                print(f'  L{li} pos{pos}: {repr(ch)} {cph} [{script}] in: {ln[:80]}')
            total_issues += len(file_issues)

if total_issues == 0:
    print('All stotra files clean — no wrong-script characters found.')
else:
    print(f'\nTotal: {total_issues} wrong-script characters across all files.')
