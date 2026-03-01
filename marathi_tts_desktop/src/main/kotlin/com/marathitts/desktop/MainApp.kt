package com.marathitts.desktop

import javafx.application.Application
import javafx.application.Platform
import javafx.fxml.FXMLLoader
import javafx.scene.Scene
import javafx.stage.Stage
import java.util.Timer
import java.util.TimerTask

class MainApp : Application() {

    override fun start(primaryStage: Stage) {
        val loader = FXMLLoader(javaClass.getResource("/fxml/MainView.fxml"))
        val root = loader.load<javafx.scene.Parent>()

        // Apply dark mode if system theme is dark
        val dark = isSystemDarkMode()
        if (dark) {
            root.styleClass.add("dark")
        }

        primaryStage.title = "मराठी TTS — Marathi Text-to-Speech"
        primaryStage.scene = Scene(root, 1100.0, 780.0)
        primaryStage.minWidth = 800.0
        primaryStage.minHeight = 600.0
        primaryStage.show()

        // Poll system theme every 5 seconds and update dynamically
        val timer = Timer(true)
        timer.schedule(object : TimerTask() {
            override fun run() {
                val isDark = isSystemDarkMode()
                Platform.runLater {
                    val hasDark = root.styleClass.contains("dark")
                    if (isDark && !hasDark) {
                        root.styleClass.add("dark")
                    } else if (!isDark && hasDark) {
                        root.styleClass.remove("dark")
                    }
                }
            }
        }, 5000L, 5000L)

        // Cancel timer when window closes
        primaryStage.setOnCloseRequest { timer.cancel() }
    }

    companion object {
        /**
         * Detect Windows dark mode by reading the registry.
         * Returns false on non-Windows or if detection fails (defaults to light).
         */
        fun isSystemDarkMode(): Boolean {
            return try {
                val os = System.getProperty("os.name", "").lowercase()
                if ("win" !in os) return false
                val process = ProcessBuilder(
                    "reg", "query",
                    "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                    "/v", "AppsUseLightTheme"
                ).redirectErrorStream(true).start()
                val output = process.inputStream.bufferedReader().readText()
                process.waitFor()
                // AppsUseLightTheme = 0x0 means dark mode is ON
                output.contains("0x0")
            } catch (_: Exception) {
                false
            }
        }
    }
}

fun main(args: Array<String>) {
    Application.launch(MainApp::class.java, *args)
}
