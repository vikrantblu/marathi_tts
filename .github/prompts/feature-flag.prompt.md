---
mode: 'agent'
description: 'Add or toggle a feature flag for work-in-progress functionality'
---

Manage feature flags for gating work-in-progress features.

**Action:** ${input:action:add, enable, disable, or list}
**Feature:** ${input:featureName:Feature flag name (e.g., FEAT_OFFLINE_PIPER)}

**Feature flags file:** `version.json` → `featureFlags` object.

**How flags work:**
1. `version.json` contains `"featureFlags": { "FEAT_NAME": true/false }`.
2. **Python bridges** read flags via:
   ```python
   import json, os
   _FLAGS = json.load(open(os.path.join(os.path.dirname(__file__), '..', '..', 'version.json')))
       .get('featureFlags', {})
   def is_enabled(flag): return _FLAGS.get(flag, False)
   ```
3. **Kotlin (mobile)** reads flags from `assets/version.json` at runtime:
   ```kotlin
   val flags = JSONObject(assets.open("version.json").reader().readText())
       .optJSONObject("featureFlags") ?: JSONObject()
   fun isEnabled(flag: String) = flags.optBoolean(flag, false)
   ```
4. Guard WIP code with `if is_enabled("FEAT_NAME"):` blocks.

**Steps for "add":**
1. Add the flag to `version.json` → `featureFlags` (default: `false`).
2. Add the guard in the relevant code files.
3. Document the flag in `docs/feature-flags.md`.

**Steps for "enable"/"disable":**
1. Toggle the boolean in `version.json`.
2. Run tests to confirm no regressions.
