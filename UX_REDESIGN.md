# Marathi TTS v4.0.0 — UX Redesign & Engineering Strategy

**Branch:** `feature/ux-redesign-v4`  
**Baseline:** `v3.0.0-stable` tag on `main`  
**Vision:** Build the world's best Marathi TTS app — simpler than Google Lens,
more powerful than any competitor, best-in-class tooling.

---

## 1. BRANCHING STRATEGY

### Branch Hierarchy

```
main (protected, production-ready)
  │
  ├── v3.0.0-stable (tag — last stable before pivot)
  │
  └── feature/ux-redesign-v4 (long-lived feature branch)
       │
       ├── feat/ux-v4/phase1-navigation     ← Tab architecture
       ├── feat/ux-v4/phase1-input-tab      ← INPUT tab consolidation
       ├── feat/ux-v4/phase1-output-tab     ← OUTPUT tab design
       ├── feat/ux-v4/phase1-me-tab         ← ME tab (history+favorites+settings)
       ├── feat/ux-v4/phase2-language-detect ← Auto language detection
       ├── feat/ux-v4/phase2-sentiment      ← Emotion auto-suggest
       ├── feat/ux-v4/phase3-kokoro         ← Kokoro TTS integration
       ├── feat/ux-v4/phase3-waveform       ← Prosody preview
       └── ... (one sub-branch per FEAT-xx)
```

### Rules

| Rule | Details |
|------|---------|
| **main** | Always deployable. Only merged from feature/ux-redesign-v4 after full test pass. |
| **feature/ux-redesign-v4** | Integration branch for v4. All phase sub-branches merge here first. |
| **feat/ux-v4/phase*-name** | Short-lived sub-branches for individual features. PR → feature/ux-redesign-v4. |
| **hotfix/*** | Emergency fixes on main. Cherry-pick back to feature branch. |
| **No force push** | Never force-push to main or feature/ux-redesign-v4. |
| **Squash merge** | Sub-branches squash-merge into feature branch for clean history. |
| **Rebase** | Feature branch rebases on main weekly to stay current. |

### Workflow

```
1. Create sub-branch:  git checkout feature/ux-redesign-v4
                        git checkout -b feat/ux-v4/phase1-navigation

2. Work + commit:       Conventional commits (feat:, fix:, refactor:, test:, docs:)

3. Test locally:        python test_all_platforms.py → ALL PASS
                        ./gradlew assembleDebug (if Android changes)

4. PR to feature:       PR feat/ux-v4/phase1-navigation → feature/ux-redesign-v4
                        CI runs automatically

5. Squash merge:        One clean commit per feature on integration branch

6. Phase complete:      PR feature/ux-redesign-v4 → main
                        Full regression test + deploy_mobile.ps1 release
```

---

## 2. VERSIONING STRATEGY

### Version Timeline

| Version | Milestone | Content |
|---------|-----------|---------|
| v3.0.0-stable | Baseline (tagged) | Current app: 13 screens, 37 features, 0 bugs |
| v4.0.0-alpha.1 | Phase 1 complete | 3-tab navigation, INPUT/OUTPUT/ME tabs |
| v4.0.0-alpha.2 | Phase 1 polished | Progressive disclosure, developer mode |
| v4.0.0-beta.1 | Phase 2 complete | Language detect, sentiment suggest |
| v4.0.0-beta.2 | Phase 2 + 3 start | + Kokoro TTS research |
| v4.0.0-rc.1 | Feature-complete | All Phase 1-3 done, regression tested |
| v4.0.0 | Release | Production-ready UX redesign |

### Versioning Rules

- **Pre-release tags** on feature branch: `v4.0.0-alpha.N`, `v4.0.0-beta.N`, `v4.0.0-rc.N`
- **Release tag** on main only: `v4.0.0`
- `versionCode` increments by 1 for every alpha/beta/rc build
- `versionName` in build.gradle.kts updated at each milestone
- CHANGELOG.md updated with each merge to feature branch

### Commit Convention

```
<type>(<scope>): <subject>

Types:  feat, fix, refactor, test, docs, style, perf, ci, chore
Scopes: nav, input, output, me, tts, bridge, prosody, test, build

Examples:
  feat(nav): replace drawer with bottom tab navigation (FEAT-40)
  refactor(input): consolidate OCR/PDF/Web into chip actions (FEAT-41)
  test(nav): add UI tests for tab switching
  docs: update copilot-instructions with new navigation map
```

---

## 3. TAGGING STRATEGY

### Tag Format

| Pattern | Purpose | Example |
|---------|---------|---------|
| `v{MAJOR}.{MINOR}.{PATCH}` | Production release | `v4.0.0` |
| `v{M}.{m}.{p}-stable` | Pre-pivot baseline | `v3.0.0-stable` |
| `v{M}.{m}.{p}-alpha.{N}` | Alpha milestone | `v4.0.0-alpha.1` |
| `v{M}.{m}.{p}-beta.{N}` | Beta milestone | `v4.0.0-beta.1` |
| `v{M}.{m}.{p}-rc.{N}` | Release candidate | `v4.0.0-rc.1` |
| `v{M}.{m}.{p}-hotfix.{N}` | Emergency fix | `v3.0.0-hotfix.1` |

### When to Tag

- **Every milestone completion** (phase done, merged to feature branch)
- **Every RC build** (tested, ready for user feedback)
- **Every production release** (merged to main)
- Tags are annotated (`git tag -a`) with description of what changed

---

## 4. DOCUMENTATION STRATEGY

### What Gets Updated and When

| Document | Updated When | By Whom |
|----------|-------------|---------|
| `CHANGELOG.md` | Every merge to feature branch | Developer |
| `FEATURES.txt` | Feature planned, started, or shipped | Developer |
| `BUGS.txt` | Bug found or fixed | Developer |
| `.github/copilot-instructions.md` | Any structural change (screen, service, route) | Developer |
| `UX_REDESIGN.md` (this file) | Strategy or wireframe changes | Developer |
| `marathi_tts_web/tts_features.md` | TTS capability changes | Developer |
| `marathi_tts_mobile/README.md` | Mobile build/feature changes | Developer |

### Code Documentation

- **Kotlin:** KDoc on public classes and non-obvious functions
- **Python:** Docstrings on public functions in TTS engine
- **XML layouts:** Comment blocks marking sections (<!-- INPUT AREA -->, etc.)
- **No over-documentation:** Don't add comments to self-explanatory code

### Architecture Decision Records (ADRs)

For significant decisions, add a brief note in CHANGELOG.md under "### Design Decisions":

```markdown
### Design Decisions
- ADR-001: Bottom tabs over drawer because user testing showed 3x faster task completion
- ADR-002: Kokoro TTS over Coqui because MIT license + active Indic language support
- ADR-003: Keep Chaquopy bridge pattern (not rewrite in Kotlin) for Python TTS engine reuse
```

---

## 5. TESTING STRATEGY

### Test Pyramid

```
                    ┌─────────┐
                    │ Manual  │  5-10 user tests per phase
                    │  QA     │  (real Marathi speakers)
                   ─┼─────────┼─
                  / │ UI Tests│ \   Espresso (Android)
                 /  │ (E2E)   │  \  Tab navigation, chip clicks
                /   └─────────┘   \
               /  ┌─────────────┐  \
              /   │ Integration │   \   test_all_platforms.py
             /    │   Tests     │    \  Bridge → Engine → Output
            /     └─────────────┘     \
           /    ┌───────────────────┐   \
          /     │   Unit Tests      │    \  Python engine, Kotlin ViewModels
         /      └───────────────────┘     \
        ───────────────────────────────────
```

### Existing Tests (Preserved)

`test_all_platforms.py` — 30+ checks across Sections A-K:
- Syntax check (18 files, 3 platforms)
- SandhiEngine (7 checks)
- Sanskrit phonetics (4 checks)
- MetreEngine (7 checks)
- ProsodyEngine integration (7 checks)
- Old Marathi phonetics (4 checks)
- Modern Marathi phonetics (5 checks)
- G2P lexicon (5 checks)
- TextNormalizer (Section I)
- GrammarEngine (Section J)
- number_to_words (Section K)

**Rule: These MUST continue to pass on every commit. No exceptions.**

### New Tests for v4.0.0

#### Phase 1 Tests (Navigation)

| Test ID | Type | What it verifies |
|---------|------|-----------------|
| T-NAV-01 | Espresso | Bottom tabs visible: INPUT, OUTPUT, ME |
| T-NAV-02 | Espresso | Tab switching works (click each, verify fragment) |
| T-NAV-03 | Espresso | Deep link to OUTPUT tab after generation |
| T-NAV-04 | Espresso | INPUT tab chip actions (OCR, PDF, Web, Voice) launch correctly |
| T-NAV-05 | Espresso | ME tab shows history, favorites, stotra sections |
| T-NAV-06 | Espresso | Developer mode toggle hides/shows TestDashboard |
| T-NAV-07 | Unit | Old drawer menu items no longer crash if deep-linked |

#### Phase 2 Tests (Intelligent Defaults)

| Test ID | Type | What it verifies |
|---------|------|-----------------|
| T-LANG-01 | Unit | Auto-detect Marathi text returns "mr" |
| T-LANG-02 | Unit | Auto-detect Sanskrit text returns "sa" |
| T-LANG-03 | Unit | Auto-detect Hindi text returns "hi" |
| T-LANG-04 | Unit | Auto-detect English text returns "en" |
| T-SENT-01 | Unit | Sad text suggests "sad" emotion |
| T-SENT-02 | Unit | Devotional text suggests "devotional" emotion |
| T-SENT-03 | Unit | Neutral text suggests "neutral" emotion |

#### Phase 3 Tests (Voice Quality)

| Test ID | Type | What it verifies |
|---------|------|-----------------|
| T-KOK-01 | Integration | Kokoro TTS generates non-empty audio for Marathi |
| T-KOK-02 | Integration | Kokoro works offline (no network) |
| T-KOK-03 | Integration | Kokoro fallback to edge-tts on failure |
| T-WAVE-01 | Unit | Waveform preview returns data points for text |
| T-WAVE-02 | Espresso | Waveform canvas renders without crash |

### CI Pipeline

```yaml
# .github/workflows/test.yml (existing, enhanced)
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r .github/ci-requirements.txt
      - run: python test_all_platforms.py
      # Future: Add Android instrumented tests
      # - run: ./gradlew connectedAndroidTest
```

### Manual QA Checklist (Per Phase)

Before merging any phase to main:

- [ ] Fresh install on physical device (not just emulator)
- [ ] Test with 3+ real Marathi texts (prose, verse, stotra)
- [ ] Test with long text (1000+ chars) — streaming works
- [ ] Test offline behavior (airplane mode)
- [ ] Test dark mode
- [ ] Test screen rotation
- [ ] Test back button behavior from every tab
- [ ] Test with system font size: Large
- [ ] Get feedback from 3+ non-technical Marathi speakers
- [ ] Performance: app cold start < 3 seconds
- [ ] Performance: TTS generation < 5 seconds for short text

---

## 6. ROLLBACK STRATEGY

### If v4.0.0 Fails

```powershell
# Revert to stable baseline
git checkout main
git reset --hard v3.0.0-stable
git push --force-with-lease origin main

# Or: deploy the v3.0.0-stable APK from backup
# C:\My_Drive_Backup\builds\marathi_tts\marathi-tts-v3.0.0-release-*.apk
```

### If a Phase Fails Mid-Development

```powershell
# Feature branch is isolated — main is untouched
# Just abandon the problematic sub-branch
git checkout feature/ux-redesign-v4
git branch -D feat/ux-v4/phase1-broken-feature

# Or: revert last merge on feature branch
git revert HEAD
```

### Safety Net

- `v3.0.0-stable` tag is immutable — always available as fallback
- main branch only receives tested, reviewed code
- APK backups at `C:\My_Drive_Backup\builds\marathi_tts\`

---

## 7. WIREFRAMES — 3-TAB ARCHITECTURE

### Tab 1: INPUT

```
┌─────────────────────────────────────────┐
│  ≡  Marathi TTS                    [⚙️] │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────────┐│
│  │                                     ││
│  │     [Large text input area]         ││
│  │     Placeholder: "Type or paste     ││
│  │     Marathi text here..."           ││
│  │                                     ││
│  │                                     ││
│  │                    [Paste] [Clear]  ││
│  └─────────────────────────────────────┘│
│                                         │
│  From:                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │
│  │ 📷   │ │ 📄   │ │ 🌐   │ │ 🎤     │ │
│  │Camera│ │ PDF  │ │ Web  │ │ Voice  │ │
│  └──────┘ └──────┘ └──────┘ └────────┘ │
│                                         │
│  Recent:                                │
│  ┌─────────────────────────────────────┐│
│  │ [chip: "नमस्कार मित्रांनो..."]       ││
│  │ [chip: "श्रीगणेशाय नमः..."]          ││
│  │ [chip: "आज मी तुम्हाला..."]          ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─────────────────────────────────────┐│
│  │         [🔊 GENERATE AUDIO]         ││
│  └─────────────────────────────────────┘│
│                                         │
├─────────────────────────────────────────┤
│  [📝 Input]   [🔊 Output]   [👤 Me]    │
└─────────────────────────────────────────┘
```

### Tab 2: OUTPUT

```
┌─────────────────────────────────────────┐
│  ≡  Audio Output                  [⚙️] │
├─────────────────────────────────────────┤
│                                         │
│  "नमस्कार मित्रांनो, आज..."              │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │  ▶️  ━━━━━━━━●━━━━━  1:23 / 2:45   ││
│  └─────────────────────────────────────┘│
│                                         │
│  Speed    ◄━━━━━●━━━━━► 1.0x           │
│  Pitch    ◄━━━━━●━━━━━► Normal         │
│  Volume   ◄━━━━━●━━━━━► 100%           │
│                                         │
│  Emotion: (auto-suggested)              │
│  [😊 Happy] [😢 Sad] [🙏 Devotional]   │
│  [😠 Angry] [😌 Peaceful] [😐 Neutral] │
│                                         │
│  ─────── Advanced ▼ ────────            │
│  (collapsed: engine, language, type)    │
│                                         │
│  ┌────────┐ ┌────────┐ ┌──────────┐    │
│  │📋 Copy │ │📤 Share│ │💾 Save   │    │
│  └────────┘ └────────┘ └──────────┘    │
│                                         │
├─────────────────────────────────────────┤
│  [📝 Input]   [🔊 Output]   [👤 Me]    │
└─────────────────────────────────────────┘
```

### Tab 3: ME

```
┌─────────────────────────────────────────┐
│  ≡  My Library                    [⚙️] │
├─────────────────────────────────────────┤
│                                         │
│  ❤️ FAVORITES                           │
│  ┌──────────────────────────────────┐   │
│  │ 1. विष्णु सहस्रनाम   ▶️  💾  🗑️  │   │
│  │ 2. राम रक्षा          ▶️  💾  🗑️  │   │
│  │ 3. गणेश अथर्वशीर्ष    ▶️  💾  🗑️  │   │
│  └──────────────────────────────────┘   │
│                                         │
│  📖 STOTRA LIBRARY                      │
│  ┌──────────────────────────────────┐   │
│  │ [Search stotras...]              │   │
│  │ • विष्णु सहस्रनाम    [▶️] [❤️]   │   │
│  │ • राम रक्षा           [▶️] [❤️]   │   │
│  │ • हनुमान चालीसा       [▶️] [❤️]   │   │
│  │ • ... 15 total                   │   │
│  └──────────────────────────────────┘   │
│                                         │
│  🕐 RECENT HISTORY                      │
│  [All] [TTS] [OCR] [PDF] [Other]       │
│  ┌──────────────────────────────────┐   │
│  │ Today: "नमस्कार..." | 2m ago     │   │
│  │ Today: PDF -> 3 pages | 1h ago   │   │
│  │ Yesterday: Stotra | 1d ago       │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ⚙️ [Settings]  📊 [Stats]             │
│                                         │
├─────────────────────────────────────────┤
│  [📝 Input]   [🔊 Output]   [👤 Me]    │
└─────────────────────────────────────────┘
```

---

## 8. SCREEN CONSOLIDATION MAP

What happens to every existing screen:

| Current Screen | v4.0.0 Location | How |
|---|---|---|
| TtsFragment | INPUT tab (main content) | Text input area + Generate button |
| EmotionFragment | OUTPUT tab (emotion chips) | Inline chip selector, not separate screen |
| SttFragment | INPUT tab (Voice chip) | Long-press mic icon or "Voice" chip |
| OcrFragment | INPUT tab (Camera chip) | 1-tap camera → extract → paste inline |
| PdfFragment | INPUT tab (PDF chip) | File picker → extract → paste inline |
| WebFetchFragment | INPUT tab (Web chip) | URL input modal → fetch → paste inline |
| CorrectionFragment | OUTPUT tab (Advanced) | Auto-run as preprocessing toggle |
| ModiFragment | OUTPUT tab (Advanced) | Script toggle in advanced options |
| StotraFragment | ME tab (Stotra Library) | Embedded section with search + favorites |
| BookReaderFragment | INPUT tab (Camera chip variant) | Camera → OCR → paste inline |
| HistoryFragment | ME tab (Recent History) | Embedded section with filter chips |
| SettingsFragment | ME tab (Settings button) | Bottom of ME tab or modal |
| TestDashboardFragment | ME tab → Settings → Developer | Hidden behind developer toggle |

---

## 9. TECH STACK ASSESSMENT

### Current (Keep)

| Component | Technology | Status |
|-----------|-----------|--------|
| UI Framework | Material3 (Material Design 3) | Best-in-class for 2026 |
| Database | Room 2.6.1 + KSP | Industry standard |
| Python Runtime | Chaquopy 15.x | Best option for embedded Python |
| Navigation | Jetpack Navigation | Keep, adapt for bottom tabs |
| Camera | CameraX | Google recommended |
| OCR | ML Kit Text Recognition | Best for Devanagari |
| Audio | MediaPlayer + pydub | Adequate for current needs |
| TTS Engines | gTTS + Edge-TTS | Good cloud engines |
| CI | GitHub Actions | Working well |

### Upgrade (Phase 2-3)

| Component | Current | Upgrade To | Why |
|-----------|---------|-----------|-----|
| Offline TTS | None | Kokoro TTS | MIT license, Indian voices, no cloud dependency |
| Sentiment | Manual emotion pick | DistilBERT or rule-based classifier | Auto-suggest emotion |
| Audio Viz | None | Canvas-based waveform | Show prosody preview |
| Language ID | Basic detection | ML Kit Language ID | Reliable multi-script detection |
| Animations | None | Material Motion | Smooth tab transitions, chip animations |

### Research Needed (Phase 3+)

| Technology | Question | Decision Point |
|-----------|----------|---------------|
| Kokoro TTS | APK size impact? Model download vs bundle? | Before Phase 3 starts |
| Jetpack Compose | Migrate from XML? Or keep XML? | After Phase 1 (assess effort) |
| Kotlin Multiplatform | Share ViewModel logic with desktop? | v5.0.0 consideration |
| ONNX Runtime Mobile | Run ML models on-device? | Phase 4 research |

---

## 10. SUCCESS METRICS

| Metric | v3.0.0 (Current) | v4.0.0 Target |
|--------|------------------|---------------|
| Time to first audio (new user) | ~45 seconds | < 15 seconds |
| Settings changes per session | 3+ (guessing) | 0-1 (smart defaults) |
| Feature discoverability | ~40% find OCR | 95% (chips on INPUT) |
| Screens user must learn | 13 | 3 |
| Taps to generate from OCR | 6+ (drawer→OCR→extract→copy→drawer→TTS→paste→generate) | 3 (chip→camera→generate) |
| Offline capability | Limited | Full (with Kokoro) |
| App cold start | ~4 seconds | < 3 seconds |

---

## 11. RISK REGISTER

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Users miss features that moved | High | Show "What's New" on first v4 launch; keep drawer as optional |
| Kokoro TTS model too large for APK | Medium | On-demand download (first use), not bundled |
| Bottom tabs don't fit all features | Medium | Overflow menu on ME tab for rare features |
| Phase 1 breaks existing Room DB | High | Room migration scripts; extensive testing |
| Chaquopy + Kokoro compatibility | Medium | Early spike in Phase 3; fallback to cloud TTS |

---

_Last updated: 2026-03-06 by Copilot on branch feature/ux-redesign-v4_
