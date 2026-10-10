// d:/ironnn/jarvis-android-companion/app/src/main/java/com/jarvis/companion/JarvisAccessibilityService.kt
package com.jarvis.companion

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class JarvisAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "JarvisAccessibility"
        private var instance: JarvisAccessibilityService? = null

        fun clickAcceptUiNode(): Boolean {
            val rootNode = instance?.rootInActiveWindow ?: return false
            Log.d(TAG, "Triggering UI inspection scan...")
            return scanAndClickAccept(rootNode)
        }

        private fun scanAndClickAccept(node: AccessibilityNodeInfo?): Boolean {
            if (node == null) return false

            val id = node.viewIdResourceName?.lowercase() ?: ""
            val text = node.text?.toString()?.lowercase() ?: ""
            val desc = node.contentDescription?.toString()?.lowercase() ?: ""

            // Target classic WhatsApp accept buttons (by ID, text, or content description chimes)
            val isAccept = id.contains("accept_btn") || 
                           id.contains("answer_btn") || 
                           id.contains("call_accept") ||
                           text.contains("answer") || 
                           text.contains("accept") ||
                           desc.contains("answer") || 
                           desc.contains("accept") ||
                           desc.contains("slide up to answer") ||
                           desc.contains("swipe up to answer")

            if (isAccept) {
                if (node.isClickable) {
                    val clicked = node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    Log.i(TAG, "Simulated click action on accept node: clicked=$clicked")
                    return clicked
                } else {
                    // Try parent nodes if node itself isn't clickable
                    var parent = node.parent
                    while (parent != null) {
                        if (parent.isClickable) {
                            val parentClicked = parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                            Log.i(TAG, "Simulated click action on parent accept node: clicked=$parentClicked")
                            return parentClicked
                        }
                        parent = parent.parent
                    }
                }
            }

            // Recurse children views
            for (i in 0 until node.childCount) {
                if (scanAndClickAccept(node.getChild(i))) {
                    return true
                }
            }
            return false
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Jarvis Accessibility UI Service connected.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val packageName = event.packageName?.toString() ?: ""
        if (packageName != "com.whatsapp") return

        Log.d(TAG, "Intercepted event from WhatsApp: ${AccessibilityEvent.eventTypeToString(event.eventType)}")
        
        // Scan for call UI state changes
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val rootNode = rootInActiveWindow
            if (rootNode != null) {
                scanCallWindow(rootNode)
            }
        }
    }

    override fun onInterrupt() {
        Log.w(TAG, "Jarvis Accessibility UI Service interrupted.")
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) {
            instance = null
        }
    }

    private fun scanCallWindow(node: AccessibilityNodeInfo) {
        // Log WhatsApp screen layouts to identify call widgets
        val stack = mutableListOf<AccessibilityNodeInfo>()
        stack.add(node)
        while (stack.isNotEmpty()) {
            val current = stack.removeAt(0)
            val id = current.viewIdResourceName ?: ""
            val text = current.text ?: ""
            val desc = current.contentDescription ?: ""
            
            if (id.isNotEmpty() || text.isNotEmpty() || desc.isNotEmpty()) {
                Log.v(TAG, "Layout node ID: $id | Text: $text | Desc: $desc")
            }
            
            for (i in 0 until current.childCount) {
                val child = current.getChild(i)
                if (child != null) stack.add(child)
            }
        }
    }
}
