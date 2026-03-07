# MCP Tools Reference

## Overview

The Marathi TTS MCP server (`.github/mcp/marathi_tts_mcp.py`) exposes 21 tools
for automated coding agents. It runs as a stdio-based MCP server configured in
`.vscode/mcp.json`.

## Tool Inventory

### Core TTS Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `run_platform_tests` | — | Run `test_all_platforms.py`, return pass/fail |
| `sync_tts_file` | `relative_path` | Copy a file from web `tts/` to desktop + mobile |
| `check_tts_syntax` | — | `ast.parse` all engine files in all 3 platforms |
| `check_tts_sync` | — | MD5-compare all `tts/` files across platforms |
| `count_tts_engine_files` | — | Count `.py` files in each platform's `tts/` tree |

### G2P & Phonetics

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_g2p_lexicon` | `query` | Grep `g2p_constants.py` for a Devanagari word |
| `get_bridge_functions` | `bridge_name` | Parse a bridge script, return public function names |

### Version & Feature Flags

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_version_json` | — | Read `version.json` contents |
| `bump_version` | `bump_type` (major/minor/patch) | Bump version in `version.json` + `build.gradle.kts` |
| `get_feature_flags` | — | List all flags from `version.json` |
| `toggle_feature_flag` | `flag_name`, `enabled` | Enable/disable a feature flag |

### Project Navigation

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_open_bugs` | — | Read `BUGS.txt` |
| `list_unreleased_features` | — | Read `FEATURES.txt` |
| `get_changelog_unreleased` | — | Extract `[Unreleased]` section from `CHANGELOG.md` |
| `get_project_version` | — | Read version from `build.gradle.kts` |
| `list_stotra_catalog` | — | Parse `stotra_catalog.json` |
| `get_mobile_nav_graph` | — | Parse `nav_graph.xml` fragment destinations |

### Testing

| Tool | Parameters | Description |
|------|-----------|-------------|
| `run_platform_tests` | — | Full test suite |
| `run_parallel_tests` | — | Run tests with parallel output |
| `get_test_sections` | — | List test sections (A–K) in `test_all_platforms.py` |
| `run_single_test_section` | `section` | Run one section only |

### Device

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_connected_adb_devices` | — | `adb devices` output |

## Configuration

`.vscode/mcp.json`:
```json
{
  "servers": {
    "marathi-tts": {
      "type": "stdio",
      "command": "python",
      "args": [".github/mcp/marathi_tts_mcp.py"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Adding a New Tool

1. Add tool definition to `TOOLS` list (name, description, inputSchema)
2. Add implementation function
3. Add entry to `TOOL_HANDLERS` dict
4. Test with: `echo '{"method":"tools/call","params":{"name":"tool_name","arguments":{}}}' | python .github/mcp/marathi_tts_mcp.py`
