package com.marathitts.mobile.ui.bookreader

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.marathitts.mobile.MainActivity

/**
 * Foreground service that keeps the CPU alive (via PARTIAL_WAKE_LOCK) while
 * the Book Reader is reading aloud, even when the screen turns off.
 *
 * The Fragment starts this service when reading begins and stops it when
 * reading ends or the user clears the page. The notification shows the
 * current sentence and a Stop button; pressing Stop sends
 * [ACTION_STOP_READING] which the Fragment catches via a local broadcast
 * receiver and routes to the ViewModel.
 */
class BookReaderForegroundService : Service() {

    companion object {
        const val CHANNEL_ID     = "book_reader_channel"
        const val NOTIF_ID       = 1001

        /** Intent action used to start / update the service notification. */
        const val ACTION_UPDATE  = "com.marathitts.mobile.READER_UPDATE"
        /** Pressed in notification → Fragment receives → viewModel.stopReading(). */
        const val ACTION_STOP_READING = "com.marathitts.mobile.STOP_READING"

        const val EXTRA_STATUS   = "status"
        const val EXTRA_SENTENCE = "sentence"
    }

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        // Acquire a PARTIAL_WAKE_LOCK — keeps CPU running, screen can turn off
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "MarathiTTS:BookReaderWakeLock"
        ).also {
            @Suppress("WakelockTimeout")
            it.acquire(4 * 60 * 60 * 1000L)  // Max 4 hours
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val status   = intent?.getStringExtra(EXTRA_STATUS)   ?: "Reading…"
        val sentence = intent?.getStringExtra(EXTRA_SENTENCE) ?: ""

        // Tap notification → open app
        val openPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            },
            PendingIntent.FLAG_IMMUTABLE
        )

        // "Stop" action in notification → broadcast → Fragment → ViewModel
        val stopPi = PendingIntent.getBroadcast(
            this, 0,
            Intent(ACTION_STOP_READING).setPackage(packageName),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle("Marathi Book Reader")
            .setContentText(status)
            .setStyle(NotificationCompat.BigTextStyle().bigText(sentence.take(200)))
            .setContentIntent(openPi)
            .addAction(android.R.drawable.ic_delete, "Stop", stopPi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        startForeground(NOTIF_ID, notification)
        return START_STICKY
    }

    override fun onDestroy() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Book Reader",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Reading progress for Marathi Book Reader"
            setSound(null, null)
            enableVibration(false)
        }
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)
    }
}
