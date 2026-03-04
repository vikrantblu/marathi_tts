package com.marathitts.desktop.util

import javafx.scene.control.Label
import javafx.scene.input.Clipboard
import javafx.scene.input.ClipboardContent

/** Copies [text] to the system clipboard and updates [statusLabel] if provided. */
fun copyToClipboard(text: String, statusLabel: Label? = null) {
    if (text.isBlank()) {
        statusLabel?.text = "Nothing to copy."
        return
    }
    val content = ClipboardContent().apply { putString(text) }
    Clipboard.getSystemClipboard().setContent(content)
    statusLabel?.text = "Copied to clipboard ✓"
}
