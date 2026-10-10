// d:/ironnn/jarvis-android-companion/app/src/main/java/com/jarvis/companion/JarvisNotificationListener.kt
package com.jarvis.companion

import android.app.Notification
import android.app.PendingIntent
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class JarvisNotificationListener : NotificationListenerService() {

    companion object {
        private const val TAG = "JarvisNotification"
        private var instance: JarvisNotificationListener? = null
        private var activeAnswerIntent: PendingIntent? = null

        fun answerActiveCall(): Boolean {
            return try {
                if (activeAnswerIntent != null) {
                    activeAnswerIntent?.send()
                    activeAnswerIntent = null
                    Log.d(TAG, "Notification Answer intent triggered successfully!")
                    true
                } else {
                    Log.w(TAG, "No active Notification Answer intent cached.")
                    false
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fire notification Answer intent", e)
                false
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        Log.i(TAG, "Jarvis Notification Listener initialized.")
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) {
            instance = null
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val packageName = sbn.packageName
        if (packageName != "com.whatsapp") return

        val extras = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE) ?: "Unknown Caller"
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        val category = sbn.notification.category

        Log.d(TAG, "WhatsApp Notification: $title - $text (Category: $category)")

        // Identify incoming voice or video WhatsApp calls
        val isCall = category == Notification.CATEGORY_CALL || 
                     text.contains("incoming voice call", ignoreCase = true) || 
                     text.contains("incoming video call", ignoreCase = true) ||
                     text.contains("incoming call", ignoreCase = true)

        if (isCall) {
            Log.w(TAG, "Incoming WhatsApp Call Detected from: $title")
            
            // Iterate over notification actions to find and cache the 'Answer' intent
            sbn.notification.actions?.forEach { action ->
                val actionTitle = action.title.toString().lowercase()
                if (actionTitle.contains("answer") || actionTitle.contains("accept")) {
                    activeAnswerIntent = action.actionIntent
                    Log.d(TAG, "Cached Call Answer PendingIntent!")
                }
            }

            // Sync caller name with J.A.R.V.I.S. Desktop over WebSocket
            MainActivity.syncPhoneEvent("incoming_call", title, text)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        if (sbn.packageName == "com.whatsapp") {
            Log.d(TAG, "WhatsApp call notification dismissed.")
            activeAnswerIntent = null
            MainActivity.syncPhoneEvent("end_call", "WhatsApp Call", "Dismissed")
        }
    }
}
