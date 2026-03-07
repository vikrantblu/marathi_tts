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
    },
    {
        "name": "bump_version",
        "description": (
            "Bump the project version in version.json and build.gradle.kts. "
            "Level can be 'major', 'minor', or 'patch'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["major", "minor", "patch"],
                    "description": "Semver bump level"
                }
            },
            "required": ["level"]
        }
    },
    {
        "name": "get_version_json",
        "description": "Return the full contents of version.json including feature flags.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_feature_flags",
        "description": "Return all feature flags and their current status from version.json.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "toggle_feature_flag",
        "description": "Enable or disable a feature flag in version.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "flag": {"type": "string", "description": "Flag name (e.g., FEAT_OFFLINE_PIPER)"},
                "enabled": {"type": "boolean", "description": "True to enable, False to disable"}
            },
            "required": ["flag", "enabled"]
        }
    },
    {
        "name": "check_tts_sync",
        "description": (
            "Verify all three platforms have identical tts/ engine files. "
            "Reports any missing or drifted files."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "list_stotra_catalog",
        "description": "Return the stotra catalog (id, name, deity) from stotra_catalog.json.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_mobile_nav_graph",
        "description": "Return the list of destinations in the mobile navigation graph.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "search_g2p_lexicon",
        "description": "Search the G2P exception lexicon for a word or pattern.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Devanagari word or substring to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "count_tts_engine_files",
        "description": "Count Python files across all three platform tts/ trees.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_bridge_functions",
        "description": "List all public functions in a bridge script.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bridge": {
                    "type": "string",
                    "description": "Bridge name (e.g., 'tts', 'emotion', 'stt', 'ocr', 'pdf', 'web', 'correction')"
                }
            },
            "required": ["bridge"]
        }
    },
    {
        "name": "get_test_sections",
        "description": "List all test sections in test_all_platforms.py with their check counts.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "run_single_test_section",
        "description": "Run a specific test section (A-K) from test_all_platforms.py.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section letter (A, B, C, D, E, F, G, H, I, J, K)"
                },
                "platform": {
                    "type": "string",
                    "description": "Platform to test (web, desktop, mobile). Default: all."
                }
            },
            "required": ["section"]
        }
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
    # Path traversal prevention: reject .. components
    if '..' in rel.split('/'):
        return "ERROR: relative_path must not contain '..'"
    import shutil
    web  = ROOT / "marathi_tts_web" / "tts" / Path(rel)
    # Verify resolved path stays within the tts directory
    web_tts_root = (ROOT / "marathi_tts_web" / "tts").resolve()
    if not str(web.resolve()).startswith(str(web_tts_root)):
        return "ERROR: relative_path escapes tts/ directory"
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


def tool_bump_version(args: dict) -> str:
    level = args.get("level", "patch")
    if level not in ("major", "minor", "patch"):
        return "ERROR: level must be 'major', 'minor', or 'patch'"
    vj_path = ROOT / "version.json"
    gradle_path = ROOT / "marathi_tts_mobile" / "app" / "build.gradle.kts"
    try:
        vj = json.loads(vj_path.read_text("utf-8"))
        parts = vj["version"].split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        if level == "major":
            major += 1; minor = 0; patch = 0
        elif level == "minor":
            minor += 1; patch = 0
        else:
            patch += 1
        new_ver = f"{major}.{minor}.{patch}"
        vj["version"] = new_ver
        vj["buildNumber"] = vj.get("buildNumber", 0) + 1
        from datetime import date
        vj["date"] = date.today().isoformat()
        vj_path.write_text(json.dumps(vj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Update build.gradle.kts
        gradle_text = gradle_path.read_text("utf-8")
        gradle_text = re.sub(r'versionName\s*=\s*"[^"]+"', f'versionName = "{new_ver}"', gradle_text)
        old_code = re.search(r'versionCode\s*=\s*(\d+)', gradle_text)
        if old_code:
            gradle_text = gradle_text.replace(
                old_code.group(0),
                f'versionCode = {int(old_code.group(1)) + 1}'
            )
        gradle_path.write_text(gradle_text, encoding="utf-8")
        return json.dumps({"version": new_ver, "buildNumber": vj["buildNumber"]}, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


def tool_get_version_json(_args: dict) -> str:
    try:
        return (ROOT / "version.json").read_text("utf-8")
    except Exception as e:
        return f"ERROR: {e}"


def tool_get_feature_flags(_args: dict) -> str:
    try:
        vj = json.loads((ROOT / "version.json").read_text("utf-8"))
        flags = vj.get("featureFlags", {})
        if not flags:
            return "No feature flags defined."
        lines = []
        for k, v in sorted(flags.items()):
            status = "✅ ON" if v else "❌ OFF"
            lines.append(f"  {k}: {status}")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def tool_toggle_feature_flag(args: dict) -> str:
    flag = args.get("flag", "").strip()
    enabled = args.get("enabled", False)
    if not flag:
        return "ERROR: flag name is required"
    vj_path = ROOT / "version.json"
    try:
        vj = json.loads(vj_path.read_text("utf-8"))
        if "featureFlags" not in vj:
            vj["featureFlags"] = {}
        vj["featureFlags"][flag] = enabled
        vj_path.write_text(json.dumps(vj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        status = "ENABLED" if enabled else "DISABLED"
        return f"{flag}: {status}"
    except Exception as e:
        return f"ERROR: {e}"


def tool_check_tts_sync(_args: dict) -> str:
    import hashlib
    web = ROOT / "marathi_tts_web" / "tts"
    desk = ROOT / "marathi_tts_desktop" / "python_bridge" / "tts"
    mob = ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "python" / "tts"
    drifted = []
    ok = 0
    for f in sorted(web.rglob("*.py")):
        rel = f.relative_to(web)
        wh = hashlib.md5(f.read_bytes()).hexdigest()
        for name, base in [("desktop", desk), ("mobile", mob)]:
            other = base / rel
            if not other.exists():
                drifted.append(f"MISSING [{name}] {rel}")
            elif hashlib.md5(other.read_bytes()).hexdigest() != wh:
                drifted.append(f"DRIFTED [{name}] {rel}")
            else:
                ok += 1
    if drifted:
        return f"{ok} in sync, {len(drifted)} issues:\n" + "\n".join(drifted)
    return f"All {ok} file pairs in sync across 3 platforms ✓"


def tool_list_stotra_catalog(_args: dict) -> str:
    catalog_path = ROOT / "marathi_tts_desktop" / "stotras" / "stotra_catalog.json"
    if not catalog_path.exists():
        catalog_path = ROOT / "marathi_tts_web" / "data" / "stotra_catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text("utf-8"))
        lines = []
        for s in catalog:
            lines.append(f"  {s.get('id', '?')} — {s.get('name', '?')} ({s.get('deity', '?')})")
        return f"{len(catalog)} stotras:\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def tool_get_mobile_nav_graph(_args: dict) -> str:
    nav_file = ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "res" / "navigation" / "nav_graph.xml"
    try:
        text = nav_file.read_text("utf-8")
        fragments = re.findall(r'android:id="@\+id/(\w+)"', text)
        labels = re.findall(r'android:label="([^"]*)"', text)
        lines = [f"  {fid}" for fid in fragments]
        return f"{len(fragments)} destinations:\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def tool_search_g2p_lexicon(args: dict) -> str:
    query = args.get("query", "").strip()
    if not query:
        return "ERROR: query is required"
    g2p_path = ROOT / "marathi_tts_web" / "tts" / "constants" / "g2p_constants.py"
    try:
        text = g2p_path.read_text("utf-8")
        matches = []
        for line in text.splitlines():
            if query in line and (":" in line or "=" in line):
                matches.append(line.strip())
        if matches:
            return f"{len(matches)} matches:\n" + "\n".join(f"  {m}" for m in matches[:30])
        return f"No matches for '{query}' in G2P lexicon."
    except Exception as e:
        return f"ERROR: {e}"


def tool_count_tts_engine_files(_args: dict) -> str:
    platforms = {
        "web":     ROOT / "marathi_tts_web" / "tts",
        "desktop": ROOT / "marathi_tts_desktop" / "python_bridge" / "tts",
        "mobile":  ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "python" / "tts",
    }
    lines = []
    total = 0
    for name, base in platforms.items():
        count = len(list(base.rglob("*.py")))
        lines.append(f"  [{name:8}] {count} files")
        total += count
    return f"Total: {total}\n" + "\n".join(lines)


def tool_get_bridge_functions(args: dict) -> str:
    bridge = args.get("bridge", "").strip()
    if not bridge:
        return "ERROR: bridge name is required"
    filename = f"{bridge}_bridge.py"
    # Check desktop first (has all bridges)
    bridge_path = ROOT / "marathi_tts_desktop" / "python_bridge" / filename
    if not bridge_path.exists():
        bridge_path = ROOT / "marathi_tts_mobile" / "app" / "src" / "main" / "python" / filename
    if not bridge_path.exists():
        return f"ERROR: bridge script not found: {filename}"
    try:
        import ast as ast_mod
        tree = ast_mod.parse(bridge_path.read_text("utf-8"))
        funcs = []
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.FunctionDef) and not node.name.startswith("_"):
                args_list = [a.arg for a in node.args.args]
                funcs.append(f"  {node.name}({', '.join(args_list)})")
        return f"{len(funcs)} public functions in {filename}:\n" + "\n".join(funcs)
    except Exception as e:
        return f"ERROR: {e}"


def tool_get_test_sections(_args: dict) -> str:
    test_file = ROOT / "test_all_platforms.py"
    try:
        text = test_file.read_text("utf-8")
        sections = re.findall(r'Section\s+([A-K])[\s:—–-]+([^\n]+)', text)
        checks = {}
        current = None
        for line in text.splitlines():
            m = re.search(r'Section\s+([A-K])', line)
            if m:
                current = m.group(1)
                checks[current] = 0
            if current and ("✓" in line or "pass" in line.lower()) and "print" in line:
                checks[current] = checks.get(current, 0) + 1
        lines = []
        for letter, name in sections:
            count = checks.get(letter, 0)
            lines.append(f"  [{letter}] {name.strip()} ({count} checks)")
        return "\n".join(lines) if lines else "Could not parse test sections."
    except Exception as e:
        return f"ERROR: {e}"


def tool_run_single_test_section(args: dict) -> str:
    section = args.get("section", "").strip().upper()
    platform = args.get("platform", "").strip()
    if not section:
        return "ERROR: section letter is required"
    cmd = [sys.executable, str(ROOT / "test_all_platforms.py")]
    if platform:
        cmd.extend(["--platform", platform])
    try:
        result = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        # Extract just the relevant section
        lines = output.splitlines()
        collecting = False
        section_lines = []
        for line in lines:
            if f"Section {section}" in line or f"section {section}" in line.lower():
                collecting = True
            if collecting:
                section_lines.append(line)
            if collecting and line.strip() == "" and len(section_lines) > 3:
                break
            if collecting and "Section" in line and f"Section {section}" not in line:
                break
        if section_lines:
            return "\n".join(section_lines)
        # Fallback: return full output
        return output[-3000:] if len(output) > 3000 else output
    except subprocess.TimeoutExpired:
        return "ERROR: test timed out after 120s"
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
    "bump_version":             tool_bump_version,
    "get_version_json":         tool_get_version_json,
    "get_feature_flags":        tool_get_feature_flags,
    "toggle_feature_flag":      tool_toggle_feature_flag,
    "check_tts_sync":           tool_check_tts_sync,
    "list_stotra_catalog":      tool_list_stotra_catalog,
    "get_mobile_nav_graph":     tool_get_mobile_nav_graph,
    "search_g2p_lexicon":       tool_search_g2p_lexicon,
    "count_tts_engine_files":   tool_count_tts_engine_files,
    "get_bridge_functions":     tool_get_bridge_functions,
    "get_test_sections":        tool_get_test_sections,
    "run_single_test_section":  tool_run_single_test_section,
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
