"""Quick parallel test runner — used for manual verification only."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

script = r'd:\marathi_tts\test_all_platforms.py'
python = sys.executable

def run_one(p):
    r = subprocess.run([python, script, '--platform', p],
                       cwd=r'd:\marathi_tts', capture_output=True, text=True, timeout=90)
    return p, r.returncode, r.stdout + r.stderr

start = time.time()
results = {}
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(run_one, p): p for p in ['web', 'desktop', 'mobile']}
    for f in as_completed(futures):
        p, code, output = f.result()
        results[p] = (code, output)

elapsed = round(time.time() - start, 1)
print(f"Ran 3 platforms in parallel ({elapsed}s):")
all_pass = True
for p in ['web', 'desktop', 'mobile']:
    code, output = results[p]
    status = 'PASS' if code == 0 else 'FAIL'
    if code != 0:
        all_pass = False
    print(f"  [{p.upper():8}] {status}")
    if code != 0:
        for line in output.splitlines():
            if any(t in line for t in ['FAIL', 'ERROR', 'SYNERR', 'MISSING', '\u2717']):
                print(f"    {line}")
print()
print('RESULT:', 'ALL PASS' if all_pass else 'FAILURES FOUND')
