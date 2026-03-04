---
mode: 'agent'
description: 'Run the cross-platform TTS test suite and fix any failures'
---

Run the offline test suite across all three platforms and fix any failures found.

**Steps:**
1. Call `run_parallel_tests` — runs web, desktop, and mobile simultaneously and returns a consolidated report. (Faster than `run_platform_tests` which runs serially.)
2. If `RESULT: ALL PASS` — report which platforms passed and elapsed time.
3. If any platform fails:
   a. Call `run_platform_tests` for just the failing platform(s) to get detailed output.
   b. Read the relevant test assertion in `test_all_platforms.py` to understand what's required.
   c. Fix in the **web** platform's `tts/` tree first (canonical source).
   d. Call `sync_tts_file` to propagate the fix to desktop and mobile.
   e. Call `run_parallel_tests` again to verify.
   f. Repeat until `RESULT: ALL PASS`.
4. Report a final summary: platforms tested, pass/fail status, files changed.

Do not report the task done until `run_parallel_tests` returns `RESULT: ALL PASS`.
