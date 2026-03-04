---
applyTo: 'marathi_tts_desktop/**'
---

# Desktop Platform Rules

- Language: **Kotlin + JavaFX** (plain FXML, no TornadoFX)
- Build: Gradle, Python bridge via subprocess (not Chaquopy)
- Package: `com.marathitts.desktop`

## Critical constraints

- **Never call Python bridge code on the JavaFX Application Thread.** Use `executor.submit { ... }` or `Platform.runLater { ... }` for results.
- Controllers are loaded by JavaFX's `FXMLLoader` — `@FXML` fields are injected, not constructed. Never `new` a controller directly.
- `fx:id="fooView"` in `MainView.fxml` injects as `fooViewController` (JavaFX naming convention: append `Controller`).
- `HistoryManager` mutations always use `Platform.runLater` internally — safe to call from any thread.
- `AudioPlayerUtil.playQueue()` is the only multi-file playback path — do not create additional `MediaPlayer` instances for sequential playback.
- For preferences, use `Preferences.userNodeForPackage(XxxController::class.java)` — all controllers in this package share the `com/marathitts/desktop/controller/` node path.
- `ClipboardUtil.copyToClipboard(text, statusLabel?)` is the single clipboard helper — do not write inline clipboard code.

## FXML conventions

- All FXMLs live in `src/main/resources/fxml/`.
- Stylesheets are at `@../css/style.css`.
- Use `styleClass="btn-primary"`, `"btn-secondary"`, `"btn-success"`, `"btn-ghost"` for buttons.
- Status labels use `styleClass="status-text"` and section headings use `"section-label"`.
