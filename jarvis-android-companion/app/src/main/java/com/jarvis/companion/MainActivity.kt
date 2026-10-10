// d:/ironnn/jarvis-android-companion/app/src/main/java/com/jarvis/companion/MainActivity.kt
package com.jarvis.companion

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var etServerIp: EditText
    private lateinit var btnConnect: Button
    private lateinit var btnPermissionNotify: Button
    private lateinit var btnPermissionAccess: Button
    private lateinit var tvLog: TextView
    private var httpClient: OkHttpClient? = null

    companion object {
        private const val TAG = "JarvisMainActivity"
        private var activeWebSocket: WebSocket? = null
        private var uiLogHandler: ((String) -> Unit)? = null

        fun syncPhoneEvent(type: String, caller: String, text: String) {
            val webSocket = activeWebSocket
            if (webSocket != null) {
                try {
                    val payload = JSONObject().apply {
                        put("type", "phone_call")
                        put("event", type)
                        put("caller", caller)
                        put("message", text)
                    }
                    webSocket.send(payload.toString())
                    Log.d(TAG, "Sent WebSocket event: $type")
                    uiLogHandler?.invoke("[WS SENT] $type from $caller")
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to send WebSocket event", e)
                }
            } else {
                Log.w(TAG, "Cannot sync phone event - WebSocket link is down.")
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etServerIp = findViewById(R.id.etServerIp)
        btnConnect = findViewById(R.id.btnConnect)
        btnPermissionNotify = findViewById(R.id.btnPermissionNotify)
        btnPermissionAccess = findViewById(R.id.btnPermissionAccess)
        tvLog = findViewById(R.id.tvLog)

        uiLogHandler = { msg ->
            runOnUiThread {
                val currentText = tvLog.text.toString()
                tvLog.text = "$msg\n$currentText"
            }
        }

        btnPermissionNotify.setOnClickListener {
            // Launch Notification Listener Settings Panel
            try {
                startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"))
                logToConsole("[SYSTEM] Redirected to Notification Listener permissions.")
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
        }

        btnPermissionAccess.setOnClickListener {
            // Launch Accessibility Settings Panel
            try {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                logToConsole("[SYSTEM] Redirected to Accessibility Service settings.")
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
        }

        btnConnect.setOnClickListener {
            val ip = etServerIp.text.toString().trim()
            if (ip.isEmpty()) {
                etServerIp.error = "IP Address required"
                return@setOnClickListener
            }
            logToConsole("[CLIENT] Launching handshake to J.A.R.V.I.S. on $ip...")
            connectWebSocket(ip)
        }
    }

    override fun onDestroy() {
        activeWebSocket?.close(1000, "Activity destroyed")
        activeWebSocket = null
        httpClient?.dispatcher?.executorService?.shutdown()
        httpClient = null
        uiLogHandler = null
        super.onDestroy()
    }

    private fun logToConsole(message: String) {
        uiLogHandler?.invoke(message)
    }

    private fun connectWebSocket(ip: String) {
        activeWebSocket?.close(1000, "Reconnecting")

        val client = httpClient ?: OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .writeTimeout(5, TimeUnit.SECONDS)
            .pingInterval(30, TimeUnit.SECONDS)
            .build()
            .also { httpClient = it }

        val wsUrl = "ws://$ip:8340/ws/voice" // Share J.A.R.V.I.S. active WS channel
        val request = Request.Builder().url(wsUrl).build()

        client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                activeWebSocket = webSocket
                Log.i(TAG, "Secure WebSocket link established to $ip")
                logToConsole("[WS LINK] Connected securely to J.A.R.V.I.S. OS!")
                
                // Identify companion client registration
                val registerPayload = JSONObject().apply {
                    put("type", "companion_handshake")
                    put("client", "AndroidCompanion")
                }
                webSocket.send(registerPayload.toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "WS Message: $text")
                try {
                    val msg = JSONObject(text)
                    val type = msg.optString("type")
                    
                    if (type == "answer_call") {
                        logToConsole("[WS INBOUND] Received automated 'Answer' signal from Desktop J.A.R.V.I.S.!")
                        
                        // Dual-Layer automation execution
                        // 1. Try Notification Action intent trigger
                        var answered = JarvisNotificationListener.answerActiveCall()
                        
                        // 2. If notification trigger fails, try UI accessibility clicker
                        if (!answered) {
                            logToConsole("[AUTOMATION] Notification action missed. Retrying with UI clicker...")
                            answered = JarvisAccessibilityService.clickAcceptUiNode()
                        }
                        
                        // Send success confirmation back to desktop
                        val reply = JSONObject().apply {
                            put("type", "answer_result")
                            put("success", answered)
                            put("method", if (answered) "automated" else "none")
                        }
                        webSocket.send(reply.toString())
                        logToConsole("[AUTOMATION] Answering process: answered=$answered")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing WebSocket message", e)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                logToConsole("[WS LINK] Closing socket connection...")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                activeWebSocket = null
                logToConsole("[WS LINK] Secure link disconnected.")
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                activeWebSocket = null
                Log.e(TAG, "WebSocket failure", t)
                logToConsole("[WS ERROR] Handshake failed: ${t.message}")
            }
        })
    }
}
