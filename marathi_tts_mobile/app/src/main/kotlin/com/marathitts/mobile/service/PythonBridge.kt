package com.marathitts.mobile.service

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.util.logging.Logger

/**
 * PythonBridge for Android — uses Chaquopy to call the bridge scripts
 * that are stored in src/main/python/.
 *
 * All heavy I/O must be called from a background thread (coroutine / Executor).
 */
object PythonBridge {

    private val log = Logger.getLogger(PythonBridge::class.java.name)
    private var initialized = false

    fun init(context: Context) {
        if (!initialized) {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(context))
            }
            // FEAT-59: Tell Python where to find user phonetic corrections
            val py = Python.getInstance()
            val os = py.getModule("os")
            os.callAttr("putenv", "USER_CORRECTIONS_PATH",
                java.io.File(context.filesDir, "user_corrections.json").absolutePath)
            initialized = true
        }
    }

    /**
     * Run a bridge module function.
     *
     * @param moduleName  Python module name (without .py), e.g. "tts_bridge"
     * @param funcName    Function to call, e.g. "generate_tts"
     * @param args        Positional args
     * @param kwargs      Keyword args as Map<String, Any?> — forwarded to Python as **kwargs
     */
    fun call(
        moduleName: String,
        funcName: String,
        args: List<Any?> = emptyList(),
        kwargs: Map<String, Any?> = emptyMap()
    ): JSONObject {
        return try {
            val py = Python.getInstance()
            val module = py.getModule(moduleName)
            // Build combined positional + keyword args array for Chaquopy
            val callArgs: Array<Any?> = buildCallArgs(args, kwargs)
            val result = module.callAttr(funcName, *callArgs)
            JSONObject(result.toString())
        } catch (e: Exception) {
            log.severe("PythonBridge.call($moduleName.$funcName) failed: ${e.message}")
            JSONObject().put("success", false).put("error", e.message ?: "Unknown error")
        }
    }

    /**
     * Combine positional args and Chaquopy Kwarg instances into a single array
     * so Chaquopy translates them correctly to Python kwargs.
     */
    private fun buildCallArgs(args: List<Any?>, kwargs: Map<String, Any?>): Array<Any?> {
        val result = mutableListOf<Any?>()
        result.addAll(args)
        // Chaquopy's com.chaquo.python.Kwarg wraps keyword arguments
        kwargs.forEach { (k, v) ->
            result.add(com.chaquo.python.Kwarg(k, v))
        }
        return result.toTypedArray()
    }

    fun isSuccess(result: JSONObject) = result.optBoolean("success", false)
    fun getError(result: JSONObject): String = result.optString("error", "Unknown error")
}
