package com.marathitts.desktop.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import java.io.File
import java.io.InputStream
import java.net.URI
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import java.util.concurrent.TimeUnit
import java.util.jar.JarFile
import java.util.logging.Logger

/**
 * PythonBridge — executes Python bridge scripts as subprocesses.
 *
 * Resolves the Python interpreter from the system PATH (or a configured
 * environment variable PYTHON_PATH), then runs the bundled bridge scripts,
 * capturing stdout as JSON.
 */
object PythonBridge {

    private val log = Logger.getLogger(PythonBridge::class.java.name)
    private val mapper = ObjectMapper().registerKotlinModule()

    /** Path to the python executable. Configurable via PYTHON_EXECUTABLE or PYTHON_PATH env-var. */
    val pythonExe: String by lazy {
        System.getenv("PYTHON_EXECUTABLE")
            ?: System.getenv("PYTHON_PATH")
            ?: listOf("python3", "python").firstOrNull { cmd ->
                runCatching {
                    ProcessBuilder(cmd, "--version").start().waitFor() == 0
                }.getOrDefault(false)
            }
            ?: "python3"
    }

    /**
     * Extract the entire `python_bridge/` resource tree (bridge scripts + `tts/` package)
     * into a temp directory on first call, then reuse that directory.
     *
     * Works in both development (gradle run / file://) and production (fat-JAR / jar://) modes.
     */
    private val bridgeDir: Path by lazy {
        val dir = Files.createTempDirectory("marathi_tts_bridge_")
        val resourceBase = "/python_bridge/"

        val resourceUrl = PythonBridge::class.java.getResource(resourceBase)
        if (resourceUrl != null && resourceUrl.protocol == "jar") {
            // ── Fat-JAR mode: walk the JAR and extract all .py files ──────────
            val jarPath = URI(resourceUrl.path.substringBefore("!")).path
            JarFile(jarPath).use { jar ->
                jar.entries().asSequence()
                    .filter { !it.isDirectory && it.name.startsWith("python_bridge/") && it.name.endsWith(".py") }
                    .forEach { entry ->
                        val relative = entry.name.removePrefix("python_bridge/")
                        val target = dir.resolve(relative)
                        Files.createDirectories(target.parent)
                        jar.getInputStream(entry).use { input ->
                            Files.copy(input, target, StandardCopyOption.REPLACE_EXISTING)
                        }
                    }
            }
        } else if (resourceUrl != null && resourceUrl.protocol == "file") {
            // ── Dev mode (gradle run): walk actual resource directory ──────────
            val rootDir = File(resourceUrl.toURI())
            rootDir.walkTopDown()
                .filter { it.isFile && it.name.endsWith(".py") }
                .forEach { file ->
                    val relative = file.relativeTo(rootDir).path
                    val target = dir.resolve(relative)
                    Files.createDirectories(target.parent)
                    Files.copy(file.toPath(), target, StandardCopyOption.REPLACE_EXISTING)
                }
        } else {
            // ── Fallback: extract the known top-level scripts by name ──────────
            listOf(
                "_bridge_logging.py",
                "tts_bridge.py", "emotion_bridge.py", "ocr_bridge.py",
                "correction_bridge.py", "pdf_bridge.py", "web_bridge.py",
                "stt_bridge.py", "script_converter_bridge.py", "setup_bridge.py"
            ).forEach { script ->
                val stream: InputStream? = PythonBridge::class.java.getResourceAsStream("$resourceBase$script")
                if (stream != null) {
                    Files.copy(stream, dir.resolve(script), StandardCopyOption.REPLACE_EXISTING)
                }
            }
        }

        log.info("Python bridge scripts extracted to: $dir")
        dir
    }

    /**
     * Run a bridge script and return the parsed JSON as a [Map].
     *
     * @param script  Script name without path, e.g. "tts_bridge.py"
     * @param args    CLI arguments to pass, e.g. listOf("--text", "मराठी")
     * @param projectRoot  Path to the marathi_tts Django project root (so Python can import tts.*)
     * @return Parsed JSON map, or a map with success=false and an error key.
     */
    fun run(script: String, args: List<String>, projectRoot: String? = null): Map<String, Any?> {
        val scriptPath = bridgeDir.resolve(script).toAbsolutePath().toString()

        // On Windows, passing long Unicode text (with quotes, newlines, special chars)
        // as CLI arguments breaks ProcessBuilder's command-line escaping.
        // Write any --text value to a temp file and substitute --text-file <path>.
        val tempFiles = mutableListOf<File>()
        val safeArgs = mutableListOf<String>()
        var i = 0
        while (i < args.size) {
            if (args[i] == "--text" && i + 1 < args.size) {
                val textFile = Files.createTempFile(bridgeDir, "arg_", ".txt").toFile()
                textFile.writeText(args[i + 1], Charsets.UTF_8)
                tempFiles += textFile
                safeArgs += "--text-file"
                safeArgs += textFile.absolutePath
                i += 2
            } else {
                safeArgs += args[i]
                i++
            }
        }

        val cmd = mutableListOf(pythonExe, scriptPath) + safeArgs

        val pb = ProcessBuilder(cmd)
            .redirectErrorStream(false)

        // Pass project root and encoding settings to the bridge process
        val env = pb.environment()
        if (projectRoot != null) {
            env["MARATHI_TTS_PROJECT_ROOT"] = projectRoot
        }
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = (projectRoot ?: "") + File.pathSeparator + (env["PYTHONPATH"] ?: "")

        return try {
            log.info("Running: ${cmd.joinToString(" ") { if (it.length > 120) it.take(120) + "…" else it }}")
            val process = pb.start()

            // Read stdout and stderr concurrently to avoid OS pipe-buffer deadlock.
            var stderr = ""
            val stderrThread = Thread({
                stderr = process.errorStream.bufferedReader(Charsets.UTF_8).readText()
            }, "bridge-stderr-reader").also { it.isDaemon = true; it.start() }

            val stdout = process.inputStream.bufferedReader(Charsets.UTF_8).readText()
            val finished = process.waitFor(300, TimeUnit.SECONDS)  // 5-min safety cap
            if (!finished) {
                process.destroyForcibly()
                log.severe("Bridge script timed out after 300s, killed: $script")
                stderrThread.join(2_000)
                return mapOf("success" to false, "error" to "Bridge script timed out (300s)",
                             "stderr" to stderr)
            }
            stderrThread.join(5_000)

            if (stderr.isNotBlank()) log.warning("Python stderr: $stderr")
            if (stdout.isBlank()) {
                mapOf("success" to false, "error" to "No output from bridge script. Stderr: $stderr")
            } else {
                @Suppress("UNCHECKED_CAST")
                mapper.readValue(stdout, Map::class.java) as Map<String, Any?>
            }
        } catch (e: Exception) {
            log.severe("Bridge error: ${e.message}")
            mapOf("success" to false, "error" to e.message)
        } finally {
            tempFiles.forEach { it.delete() }
        }
    }

    fun isSuccess(result: Map<String, Any?>): Boolean =
        result["success"] == true

    fun getError(result: Map<String, Any?>): String =
        result["error"]?.toString() ?: "Unknown error"
}
