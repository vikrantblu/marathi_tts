package com.marathitts.mobile.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import com.marathitts.mobile.MainActivity
import com.marathitts.mobile.R

/**
 * Home screen widget for quick TTS — FEAT-77.
 *
 * Two buttons:
 *   1. "Speak Clipboard" → launches MainActivity with clipboard text + auto-generate
 *   2. "Open" → launches MainActivity normally
 */
class TtsWidget : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId)
        }
    }

    companion object {
        private fun updateAppWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int
        ) {
            val views = RemoteViews(context.packageName, R.layout.widget_tts)

            // "Speak Clipboard" button → launch with auto-generate flag
            val speakIntent = Intent(context, MainActivity::class.java).apply {
                action = MainActivity.ACTION_WIDGET_SPEAK
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val speakPendingIntent = PendingIntent.getActivity(
                context, 0, speakIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.btn_speak_clipboard, speakPendingIntent)

            // "Open" button → launch normally
            val openIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val openPendingIntent = PendingIntent.getActivity(
                context, 1, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.btn_open_app, openPendingIntent)

            // Tap app icon = same as Open
            views.setOnClickPendingIntent(R.id.widget_icon, openPendingIntent)

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }
}
