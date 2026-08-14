/**
 * J.A.R.V.I.S. Unified Input v2.2
 * Handles BOTH text typing AND voice input.
 * Shows EXACT connection status and errors.
 * Works with or without API keys.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Send, AlertCircle, CheckCircle, Wifi, WifiOff, Loader2, Keyboard } from 'lucide-react';

interface UnifiedInputProps {
  onCommand?: (text: string) => void;
  backendUrl?: string;
}

export function UnifiedInput({ onCommand, backendUrl = window.location.origin }: UnifiedInputProps) {
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting');
  const [lastResponse, setLastResponse] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [useRestFallback, setUseRestFallback] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ─── Browser TTS ───
  const speakBrowser = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.0;
    u.pitch = 0.9;
    const voices = speechSynthesis.getVoices();
    const v = voices.find(v => v.name.includes('Daniel') || v.name.includes('Google UK English Male'));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }, []);

  // ─── WebSocket Connection ───
  const connectWS = useCallback(() => {
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/voice';
    console.log('[UnifiedInput] Connecting to:', wsUrl);
    
    setWsStatus('connecting');
    setErrorMsg('');
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('[UnifiedInput] WebSocket CONNECTED');
        setWsStatus('connected');
        setErrorMsg('');
        setUseRestFallback(false);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[UnifiedInput] WS message:', data.type);
          
          if (data.type === 'connected') {
            setLastResponse(data.message);
          }
          else if (data.type === 'status') {
            setIsProcessing(data.state === 'processing');
          }
          else if (data.type === 'response') {
            setLastResponse(data.text);
            setIsProcessing(false);
            onCommand?.(data.text);
          }
          else if (data.type === 'tts_fallback') {
            // Browser speaks
            speakBrowser(data.text);
          }
          else if (data.type === 'error') {
            setErrorMsg(data.message);
            setIsProcessing(false);
          }
        } catch (e) {
          console.log('[UnifiedInput] Raw WS data:', event.data);
        }
      };
      
      ws.onerror = (e) => {
        console.error('[UnifiedInput] WebSocket ERROR:', e);
        setWsStatus('error');
        setErrorMsg('WebSocket connection failed. Falling back to REST API.');
        setUseRestFallback(true);
      };
      
      ws.onclose = (e) => {
        console.log('[UnifiedInput] WebSocket CLOSED:', e.code, e.reason);
        setWsStatus('disconnected');
        // Auto-reconnect
        setTimeout(() => {
          if (wsRef.current?.readyState !== WebSocket.OPEN) {
            connectWS();
          }
        }, 3000);
      };
      
    } catch (e) {
      console.error('[UnifiedInput] Failed to create WebSocket:', e);
      setWsStatus('error');
      setUseRestFallback(true);
    }
  }, [backendUrl, onCommand, speakBrowser]);

  // Connect on mount
  useEffect(() => {
    connectWS();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWS]);

  // ─── Send Text Command ───
  const sendText = useCallback(async () => {
    if (!inputText.trim() || isProcessing) return;
    
    const text = inputText.trim();
    setInputText('');
    setIsProcessing(true);
    setErrorMsg('');
    
    // Try WebSocket first
    if (wsRef.current?.readyState === WebSocket.OPEN && !useRestFallback) {
      console.log('[UnifiedInput] Sending via WebSocket:', text);
      wsRef.current.send(JSON.stringify({
        type: 'text_command',
        text: text
      }));
      return;
    }
    
    // Fallback to REST API
    console.log('[UnifiedInput] Sending via REST:', text);
    try {
      const res = await fetch(`${backendUrl}/voice/text-command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      setLastResponse(data.response);
      speakBrowser(data.response);
      onCommand?.(data.response);
      
    } catch (e: any) {
      console.error('[UnifiedInput] REST failed:', e);
      setErrorMsg(`Failed to send: ${e.message}. Is the backend running on ${backendUrl}?`);
      setLastResponse('');
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, isProcessing, useRestFallback, backendUrl, onCommand, speakBrowser]);

  // ─── Voice Recording (Simple) ───
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };
      
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const buffer = await blob.arrayBuffer();
        
        // Send to WebSocket
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(buffer);
        } else {
          setErrorMsg('WebSocket not connected. Cannot send voice.');
        }
        
        stream.getTracks().forEach(t => t.stop());
      };
      
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      
    } catch (e: any) {
      setErrorMsg(`Microphone error: ${e.message}`);
    }
  }, []);
  
  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }, []);

  // ─── Keyboard Shortcuts ───
  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendText();
    }
  }, [sendText]);

  return (
    <div className="w-full max-w-2xl mx-auto space-y-3">
      {/* Connection Status Bar */}
      <div className="flex items-center justify-between text-[10px] font-mono tracking-wider">
        <div className="flex items-center gap-2">
          {wsStatus === 'connected' && (
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle className="w-3 h-3" /> WS CONNECTED
            </span>
          )}
          {wsStatus === 'connecting' && (
            <span className="flex items-center gap-1 text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" /> CONNECTING...
            </span>
          )}
          {wsStatus === 'error' && (
            <span className="flex items-center gap-1 text-red-400">
              <WifiOff className="w-3 h-3" /> WS FAILED
            </span>
          )}
          {wsStatus === 'disconnected' && (
            <span className="flex items-center gap-1 text-slate-500">
              <WifiOff className="w-3 h-3" /> DISCONNECTED
            </span>
          )}
          
          {useRestFallback && (
            <span className="px-1.5 py-0.5 rounded bg-blue-900/40 border border-blue-700/30 text-blue-400">
              REST FALLBACK
            </span>
          )}
        </div>
        
        <span className="text-slate-600">
          {backendUrl}
        </span>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-red-900/20 border border-red-800/30 text-red-400 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Response Display */}
      {lastResponse && (
        <div className="p-3 rounded-lg bg-blue-900/20 border border-blue-800/30">
          <p className="text-[10px] text-blue-400 uppercase tracking-wider mb-1">J.A.R.V.I.S.</p>
          <p className="text-sm text-blue-100">{lastResponse}</p>
        </div>
      )}

      {/* Input Bar */}
      <div className="flex items-center gap-2">
        {/* Voice Button */}
        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          className={`
            shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all
            ${isRecording 
              ? 'bg-red-600 animate-pulse' 
              : 'bg-slate-800 hover:bg-slate-700 border border-slate-700'
            }
          `}
          title="Hold to record voice"
        >
          <Mic className={`w-4 h-4 ${isRecording ? 'text-white' : 'text-slate-400'}`} />
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={isProcessing}
            placeholder="// Type a command, sir..."
            className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-3 pr-10 py-2.5 
                       text-sm text-cyan-100 placeholder-slate-600 font-mono
                       focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none
                       disabled:opacity-50"
          />
          <Keyboard className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
        </div>

        {/* Send Button */}
        <button
          onClick={sendText}
          disabled={!inputText.trim() || isProcessing}
          className="shrink-0 w-10 h-10 rounded-full bg-cyan-600 hover:bg-cyan-500 
                     disabled:bg-slate-800 disabled:text-slate-600
                     flex items-center justify-center transition-all"
        >
          {isProcessing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Debug Info */}
      <div className="text-[9px] text-slate-700 font-mono text-center">
        WS: {wsStatus} | REST: {useRestFallback ? 'active' : 'standby'} | 
        Recording: {isRecording ? 'YES' : 'no'} | 
        Processing: {isProcessing ? 'YES' : 'no'}
      </div>
    </div>
  );
}
