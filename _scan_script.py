import sys, io, re, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'd:\marathi_tts\marathi_tts_mobile\app\src\main\assets\stotras\vishnu_sahasranama.txt', encoding='utf-8') as f:
    lines = f.readlines()

ok_chars = set(' \t\n.,;:?!-()[]{}|/\\"') | {'\u2019','\u2018','\u201c','\u201d'}

for i, line in enumerate(lines, 1):
    bad = []
    for j, ch in enumerate(line):
        cp = ord(ch)
        is_dev  = 0x0900 <= cp <= 0x097F
        is_danda = ch in '\u0964\u0965'
        is_digit = ('0' <= ch <= '9') or ('\u0966' <= ch <= '\u096F')
        is_om   = ch == '\u0950'
        is_ok   = ch in ok_chars or ch.isascii()
        if not (is_dev or is_danda or is_digit or is_om or is_ok):
            bad.append((j, ch, hex(cp), unicodedata.name(ch, 'UNKNOWN')))
    if bad:
        print(f'L{i}: {line.rstrip()}')
        for pos, ch, cph, name in bad:
            print(f'  pos {pos}: {repr(ch)} {cph} [{name}]')
