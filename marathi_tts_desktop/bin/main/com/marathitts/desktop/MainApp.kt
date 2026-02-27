package com.marathitts.desktop

import javafx.application.Application
import javafx.fxml.FXMLLoader
import javafx.scene.Scene
import javafx.stage.Stage

class MainApp : Application() {

    override fun start(primaryStage: Stage) {
        val loader = FXMLLoader(javaClass.getResource("/fxml/MainView.fxml"))
        val root = loader.load<javafx.scene.Parent>()

        primaryStage.title = "मराठी TTS — Marathi Text-to-Speech"
        primaryStage.scene = Scene(root, 1100.0, 780.0)
        primaryStage.minWidth = 800.0
        primaryStage.minHeight = 600.0
        primaryStage.show()
    }
}

fun main(args: Array<String>) {
    Application.launch(MainApp::class.java, *args)
}
