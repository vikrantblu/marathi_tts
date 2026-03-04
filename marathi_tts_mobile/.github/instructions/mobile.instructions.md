---
applyTo: 'marathi_tts_mobile/**'
---

# Mobile Platform Rules

- Language: **Kotlin** (coroutines, `viewModelScope`, `StateFlow`)
- Build: Gradle + Chaquopy (Python 3.11 embedded in APK)
- Min SDK 26, Target SDK 34, package `com.marathitts.mobile`

## Critical constraints

- **Never call Python bridge code on the main/UI thread.** Always use `Dispatchers.IO` or `viewModelScope.launch(Dispatchers.IO)`.
- **PythonBridge is a singleton.** Never instantiate it more than once per process.
- `AudioPlayerService` is a foreground service — always call `startForegroundService()` before binding, and call `stopSelf()` when the queue is empty.
- **FileProvider is required** for sharing audio files. Uri must be obtained via `FileProvider.getUriForFile()`, not `Uri.fromFile()`. Paths are declared in `file_paths.xml`.
- `OutputActions` static helpers handle all copy/share/save — do not write new clipboard or MediaStore code inline in fragments.
- `HistoryLogger` is fire-and-forget (IO dispatcher). Never `await` it on the UI thread.
- Fragment arguments via `Bundle` only — never pass data between fragments via static fields.
- Room DB access via `AppDatabase.getDatabase(context).xxxDao()` — never create DAOs directly.
- `AppPreferences` is the only place for SharedPreferences — add any new keys as typed properties there.

## Navigation

Pattern is `DrawerLayout` + `NavHostFragment`. All fragments are top-level destinations. Use `findNavController().navigate(R.id.xxFragment)` with `popUpTo` set to avoid back-stack accumulation.
