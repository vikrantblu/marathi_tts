"""
Marathi TTS — MCP Server
Exposes project-specific tools to GitHub Copilot Agent.

Start: python .github/mcp/marathi_tts_mcp.py
Port:  stdio (VS Code MCP over stdin/stdout)
"""

import json
import sys
import subprocess
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # d:\marathi_tts

# ── MCP protocol helpers ────────────────────────────────────────────────────

def send(obj: dict):
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()

def respond(id_, result):
    send({"jsonrpc": "2.0", "id": id_, "result": result})

def error(id_, code: int, msg: str):
    send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}})

# ── Tool definitions ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "run_platform_tests",
        "description": (
            "Run test_all_platforms.py and return a structured pass/fail summary. "
            "Use this after any change to tts/ engine files to verify correctness."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Optional: run only one section (e.g. 'A', 'B', 'syntax'). Leave blank for all."
                }
            },
            "required": []
        }
    },
    {
        "name": "run_parallel_tests",
        "description": (
            "Run test_all_platforms.py for all three platforms (web, desktop, mobile) "
            "simultaneously in parallel subprocesses and return a consolidated pass/fail "
            "report. Faster than run_platform_tests for full verification after engine changes."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_project_version",
        "description": "Return the current versionName and versionCode from the mobile app's build.gradle.kts.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "list_open_bugs",
        "description": "Return all open (unfixed) bugs from BUGS.txt.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "list_unreleased_features",
        "description": "Return all features marked [Unreleased] in FEATURES.txt.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "sync_tts_file",
        "description": (
            "Copy a tts/ engine file from the canonical web platform to desktop and mobile. "
            "Provide the relative path inside tts/ (e.g. 'utils/phonetic/marathi_phonetics.py')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "Path relative to tts/ root, e.g. 'utils/phonetic/marathi_phonetics.py'"
                }
            },
            "required": ["relative_path"]
        }
    },
    {
        "name": "get_changelog_unreleased",
        "description": "Return the [Unreleased] section of CHANGELOG.md.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "check_tts_syntax",
        "description": (
            "Run a Python syntax check on all tts/ engine files across all three platforms. "
            "Reports any files with syntax errors."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "list_connected_adb_devices",
        "description": "Return the list of Android devices/emulators currently connected via ADB.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    }
]

# ── Tool implementations ────────────────────────────────────────────────────

def tool_run_platform_tests(args: dict) -> str:
    section = args.get("section", "").strip()
    cmd = [sys.executable, str(ROOT / "test_all_platforms.py")]
    try:
        result = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        # Extract summary line
        lines = output.splitlines()
        summary = [l for l in lines if "PASS" in l or "FAIL" in l or "ERROR" in l or "Section" in l]
        return "\n".join(summary) if summary else output[-3000:]
    except subprocess.TimeoutExpired:
        return "ERROR: test timed out after 120s"
    except Exception as e:
        return f"ERROR: {e}"


def tool_run_parallel_tests(_args: dict) -> str:
    """Run test_all_platforms.py for all 3 platforms simultaneously."""
    script = str(ROOT / "test_all_platforms.py")
    platforms = ["web", "desktop", "mobile"]

    def run_one(platform: str) -> tuple[str, int, str]:
        try:
            r = subprocess.run(
                [sys.executable, script, "--platform", platform],
                cwd=str(ROOT), capture_output=True, text=True, timeout=90
            )
            return platform, r.returncode, (r.stdout + r.stderr).strip()
        except subprocess.TimeoutExpired:
            return platform, 1, "ERROR: timed out after 90s"
        except Exception as e:
            return platform, 1, f"ERROR: {e}"

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_one, p): p for p in platforms}
        for future in as_completed(futures):
            platform, code, output = future.result()
            results[platform] = (code, output)

    # Consolidated report
    lines = ["=" * 60, "PARALLEL TEST RESULTS", "=" * 60]
    all_pass = True
    for p in platforms:
        code, output = results[p]
        status = "PASS" if code == 0 else "FAIL"
        if code != 0:
            all_pass = False
        lines.append(f"[{p.upper():8}] {status}")
        # Include failure details only
        if code != 0:
            fail_lines = [l for l in output.splitlines() if "✗" in l or "FAIL" in l or "ERROR" in l or "SYNERR" in l or "MISSING" in l]
            lines.extend(f"  {l}" for l in fail_lines[:20])
    lines.append("=" * 60)
    lines.append("RESULT: ALL PASS" if all_pass else "RESULT: FAILURES FOUND")
    return "\n".join(lines)


def tool_get_project_version(_args: dict) -> str:
    gradle = ROOT / "marathi_tts_mobile" / "app" / "build.gradle.kts"
    try:
        text = gradle.read_text(encoding="utf-8")
        code = re.search(r'versionCode\s*=\s*(\d+)', text)
        name = re.search(r'versionName\s*=\s*"([^"]+)"', text)
        return json.dumps({
            "versionName": name.group(1) if name else "unknown",
            "versionCode": int(code.group(1)) if code else -1,
            "file": str(gradle)
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


def tool_list_open_bugs(_args: dict) -> str:
    bugs_file = ROOT / "BUGS.txt"
    try:
        text = bugs_file.read_text(encoding="utf-8")
        # Extract everything between ## Open and ## Fixed (or end of file)
        m = re.search(r'## Open\s*(.*?)(?=## Fixed|## Closed|$)', text, re.DOTALL)
        if m:
            open_section = m.group(1).strip()
            return open_section if open_section else "No open bugs."
        return text
    except Exception as e:
        return f"ERROR: {e}"


def tool_list_unreleased_features(_args: dict) -> str:
    feat_file = ROOT / "FEATURES.txt"
    try:
        text = feat_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        collecting = False
        result = []
        for line in lines:
            if "[Unreleased]" in line or ("##" in line and "Planned" in line):
                collecting = True
            if collecting:
                result.append(line)
            if collecting and line.startswith("## ") and "Planned" not in line and "Unreleased" not in line:
                break
        # Also grep for [Unreleased] tags inline
        unreleased = [l for l in lines if "[Unreleased]" in l]
        return "\n".join(unreleased) if unreleased else "\n".join(result) if result else "None found."
    except Exception as e:
        return f"ERROR: {e}"


def tool_sync_tts_file(args: dict) -> str:
    rel = args.get("relative_path", "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        return "ERROR: relative_path is required"
    import shutil
    web  = ROOT / "marathi_tts_web" / "tts" / Path(rel)
    desk = ROOT / "marathi_tts_desktop" / "python_bridge" / "tts" / Path(rel)
    mob  = ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "python" / "tts" / Path(rel)
    if not web.exists():
        return f"ERROR: source file not found: {web}"
    results = []
    for dst in [desk, mob]:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(web), str(dst))
            results.append(f"✓ Synced → {dst}")
        except Exception as e:
            results.append(f"✗ Failed → {dst}: {e}")
    return "\n".join(results)


def tool_get_changelog_unreleased(_args: dict) -> str:
    changelog = ROOT / "CHANGELOG.md"
    try:
        text = changelog.read_text(encoding="utf-8")
        m = re.search(r'## \[Unreleased\](.*?)(?=^## \[)', text, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(0).strip()
        return "No [Unreleased] section found."
    except Exception as e:
        return f"ERROR: {e}"


def tool_check_tts_syntax(_args: dict) -> str:
    import ast
    platforms = {
        "web":     ROOT / "marathi_tts_web" / "tts",
        "desktop": ROOT / "marathi_tts_desktop" / "python_bridge" / "tts",
        "mobile":  ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "python" / "tts",
    }
    errors = []
    ok = 0
    for platform, base in platforms.items():
        for py in base.rglob("*.py"):
            try:
                ast.parse(py.read_text(encoding="utf-8"))
                ok += 1
            except SyntaxError as e:
                errors.append(f"[{platform}] {py.relative_to(ROOT)}: {e}")
    if errors:
        return f"{ok} files OK, {len(errors)} with errors:\n" + "\n".join(errors)
    return f"All {ok} files syntax-clean ✓"


def tool_list_connected_adb_devices(_args: dict) -> str:
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or result.stderr.strip() or "No output from adb"
    except FileNotFoundError:
        return "ERROR: adb not found. Is Android SDK platform-tools in PATH?"
    except Exception as e:
        return f"ERROR: {e}"


TOOL_HANDLERS = {
    "run_platform_tests":         tool_run_platform_tests,
    "run_parallel_tests":         tool_run_parallel_tests,
    "get_project_version":        tool_get_project_version,
    "list_open_bugs":           tool_list_open_bugs,
    "list_unreleased_features": tool_list_unreleased_features,
    "sync_tts_file":            tool_sync_tts_file,
    "get_changelog_unreleased": tool_get_changelog_unreleased,
    "check_tts_syntax":         tool_check_tts_syntax,
    "list_connected_adb_devices": tool_list_connected_adb_devices,
}

# ── MCP main loop ───────────────────────────────────────────────────────────

def handle(msg: dict):
    method = msg.get("method", "")
    id_ = msg.get("id")

    if method == "initialize":
        respond(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "marathi-tts-mcp", "version": "1.0.0"}
        })
    elif method == "tools/list":
        respond(id_, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name", "")
        args = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            error(id_, -32601, f"Unknown tool: {name}")
            return
        try:
            result_text = handler(args)
            respond(id_, {
                "content": [{"type": "text", "text": result_text}],
                "isError": False
            })
        except Exception as e:
            respond(id_, {
                "content": [{"type": "text", "text": f"Tool error: {e}"}],
                "isError": True
            })
    elif method == "notifications/initialized":
        pass  # no response needed
    else:
        if id_ is not None:
            error(id_, -32601, f"Method not found: {method}")


def main():
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        handle(msg)


if __name__ == "__main__":
    main()
