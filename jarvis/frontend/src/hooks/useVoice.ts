/**
 * J.A.R.V.I.S. Voice Hook v2.1
 * Zero-API-Key Mode | Push-to-Talk | Conversation Memory | Browser STT Fallback
 */
import { useState, useRef, useCallback, useEffect } from 'react';

interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
  isPushToTalk: boolean;
  transcript: string;
  responseText: string;
  status: 'idle' | 'wake' | 'listening' | 'push_to_talk' | 'processing' | 'speaking' | 'error';
  error: string | null;
  apiStatus: { stt: boolean; llm: boolean; tts: boolean };
  memoryCount: number;
}

export function useVoice() {
  const [state, setState] = useState<VoiceState>({
    isListening: false,
    isSpeaking: false,
    isPushToTalk: false,
    transcript: '',
    responseText: '',
    status: 'idle',
    error: null,
    apiStatus: { stt: false, llm: false, tts: false },
    memoryCount: 0
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const pushToTalkRef = useRef(false);
  const browserRecognitionRef = useRef<any>(null);
  const wakeRecognitionRef = useRef<any>(null);

  const playActivationSound = useCallback(() => {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.15);
    } catch {}
  }, []);

  const speakBrowser = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.1;
    u.pitch = 0.9;
    
    const voices = speechSynthesis.getVoices();
    const jarvisVoice = voices.find(v => 
      v.name.includes('Daniel') || 
      v.name.includes('Google UK English Male') ||
      v.name.includes('Fred') ||
      (v.lang === 'en-GB' && v.name.includes('Male'))
    );
    if (jarvisVoice) u.voice = jarvisVoice;
    
    u.onstart = () => setState(s => ({ ...s, isSpeaking: true, status: 'speaking' }));
    u.onend = () => setState(s => ({ ...s, isSpeaking: false, status: 'idle' }));
    
    speechSynthesis.speak(u);
  }, []);

  const startBrowserSTT = useCallback((mode: 'wake' | 'command') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setState(s => ({ ...s, error: 'Browser STT not supported', status: 'error' }));
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = mode === 'wake';
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    let finalTranscript = '';
    
    recognition.onresult = (event: any) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interim = transcript;
        }
      }
      
      if (mode === 'wake') {
        const text = (finalTranscript + interim).toLowerCase();
        if (text.includes('hey jarvis') || text.includes('jarvis')) {
          recognition.stop();
          wakeRecognitionRef.current = null;
          setState(s => ({ ...s, status: 'wake', responseText: 'Yes, sir?' }));
          playActivationSound();
          setTimeout(() => startBrowserSTT('command'), 500);
        }
      } else if (mode === 'command') {
        setState(s => ({ ...s, transcript: interim || finalTranscript }));
        if (finalTranscript.trim()) {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'browser_stt_result',
              text: finalTranscript.trim()
            }));
          }
          recognition.stop();
          browserRecognitionRef.current = null;
        }
      }
    };
    
    recognition.onerror = (e: any) => {
      if (e.error === 'no-speech') return;
      console.log('Browser STT error:', e.error);
    };
    
    recognition.onend = () => {
      if (mode === 'wake' && wakeRecognitionRef.current === recognition) {
        setTimeout(() => {
          if (state.status === 'idle') startBrowserSTT('wake');
        }, 500);
      }
    };
    
    try {
      recognition.start();
    } catch (e) {}
    
    if (mode === 'wake') wakeRecognitionRef.current = recognition;
    else browserRecognitionRef.current = recognition;
  }, [speakBrowser, playActivationSound, state.status]);

  const startPushToTalk = useCallback(() => {
    pushToTalkRef.current = true;
    setState(s => ({ ...s, isPushToTalk: true, status: 'push_to_talk' }));
    
    wsRef.current?.send(JSON.stringify({ type: 'push_to_talk_start' }));
    
    navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
    }).then(stream => {
      mediaStreamRef.current = stream;
      const ctx = new AudioContext({ sampleRate: 16000 });
      const src = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(512, 1, 1);
      
      proc.onaudioprocess = (e) => {
        if (!pushToTalkRef.current || !wsRef.current) return;
        const data = e.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(data.length);
        for (let i = 0; i < data.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, data[i] * 32768));
        }
        wsRef.current.send(int16.buffer);
      };
      
      src.connect(proc);
      proc.connect(ctx.destination);
      processorRef.current = proc;
    }).catch(e => {
      console.error("Mic access error:", e);
    });
  }, []);

  const endPushToTalk = useCallback(() => {
    pushToTalkRef.current = false;
    setState(s => ({ ...s, isPushToTalk: false, status: 'processing' }));
    
    processorRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    processorRef.current = null;
    mediaStreamRef.current = null;
    
    wsRef.current?.send(JSON.stringify({ type: 'push_to_talk_end' }));
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.code === 'Space' && !e.repeat && (!target || (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA'))) {
        e.preventDefault();
        if (state.status === 'idle') startPushToTalk();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.code === 'Space' && (!target || (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA'))) {
        e.preventDefault();
        if (state.isPushToTalk) endPushToTalk();
      }
    };
    
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [state.status, state.isPushToTalk, startPushToTalk, endPushToTalk]);

  const connect = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/voice`);
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = () => {
      console.log('Voice WS connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'status':
          setState(s => ({
            ...s,
            status: data.state || 'idle',
            apiStatus: data.api_keys || s.apiStatus
          }));
          break;
          
        case 'wake_word':
          setState(s => ({ ...s, status: 'wake', responseText: data.message }));
          playActivationSound();
          break;
          
        case 'transcript':
          setState(s => ({ ...s, transcript: data.text }));
          break;
          
        case 'llm_token':
          setState(s => ({ ...s, responseText: s.responseText + data.text }));
          break;
          
        case 'tts_chunk':
          if (data.done) {
            setState(s => ({ ...s, isSpeaking: false, status: 'idle' }));
          } else {
            const binary = atob(data.audio);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.onended = () => URL.revokeObjectURL(url);
            audio.play().catch(() => {});
            setState(s => ({ ...s, isSpeaking: true }));
          }
          break;
          
        case 'tts_fallback':
          speakBrowser(data.text);
          break;
          
        case 'stt_fallback':
          if (data.reason === 'no_api_key') {
            startBrowserSTT('command');
          }
          break;
          
        case 'error':
          setState(s => ({ ...s, error: data.message, status: 'error' }));
          break;
      }
    };
    
    ws.onclose = () => {
      setState(s => ({ ...s, isListening: false, status: 'idle' }));
      setTimeout(connect, 3000);
    };
    
    wsRef.current = ws;
  }, [speakBrowser, startBrowserSTT, playActivationSound]);

  const disconnect = useCallback(() => {
    wakeRecognitionRef.current?.stop();
    browserRecognitionRef.current?.stop();
    wsRef.current?.close();
  }, []);

  const clearMemory = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'clear_memory' }));
    setState(s => ({ ...s, memoryCount: 0 }));
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    startPushToTalk,
    endPushToTalk,
    clearMemory
  };
}
