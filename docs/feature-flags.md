# Feature Flags

## Overview

Feature flags gate work-in-progress functionality so incomplete features don't
affect production behavior. Flags are stored in `version.json` under the
`featureFlags` object.

## Current Flags

| Flag | Default | Description |
|------|---------|-------------|
| `FEAT_OFFLINE_PIPER` | `false` | Offline Piper VITS TTS (FEAT-70) |
| `FEAT_ONDEVICE_WHISPER` | `false` | On-device Whisper STT (FEAT-71) |
| `FEAT_WORD_HIGHLIGHT` | `false` | Word-level playback highlighting (FEAT-75) |

## How to use

### Python (bridge scripts)

```python
import json, os

_VERSION_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'version.json')

def _load_flags():
    try:
        with open(_VERSION_PATH, 'r', encoding='utf-8') as f:
            return json.load(f).get('featureFlags', {})
    except Exception:
        return {}

_FLAGS = _load_flags()

def is_feature_enabled(flag: str) -> bool:
    return _FLAGS.get(flag, False)
```

Usage:
```python
if is_feature_enabled('FEAT_OFFLINE_PIPER'):
    result = _generate_piper_audio(text)
    if result:
        return result
# fallback to online engine
```

### Kotlin (Android)

Read from assets at app startup:
```kotlin
val flagsJson = context.assets.open("version.json").bufferedReader().readText()
val flags = JSONObject(flagsJson).optJSONObject("featureFlags") ?: JSONObject()

fun isFeatureEnabled(flag: String): Boolean = flags.optBoolean(flag, false)
```

## Managing flags

### Via MCP tools
```
toggle_feature_flag(flag="FEAT_OFFLINE_PIPER", enabled=true)
get_feature_flags()
```

### Via agent prompt
Use the `feature-flag` prompt: add/enable/disable/list flags.

### Manually
Edit `version.json` → `featureFlags` → set boolean value.

## Lifecycle

1. **Add flag** (default: `false`) when starting a WIP feature
2. **Guard all WIP code** with `if is_feature_enabled("FLAG"):`
3. **Enable** for testing: set to `true` in version.json
4. **Remove flag** when feature is stable and shipped — replace guards with direct calls
