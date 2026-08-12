/**
 * J.A.R.V.I.S. Voice Hook v2.0
 * Wake word detection, streaming audio, low-latency TTS playback.
 */
import { useState, useRef, useCallback, useEffect } from 'react';

interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  responseText: string;
  status: 'idle' | 'wake' | 'listening' | 'processing' | 'speaking' | 'error';
  error: string | null;
}

export function useVoice() {
  const [state, setState] = useState<VoiceState>({
    isListening: false,
    isSpeaking: false,
    transcript: '',
    responseText: '',
    status: 'idle',
    error: null
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);

  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: 24000 });
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  const queueAudioChunk = useCallback((base64Audio: string) => {
    if (!base64Audio) return;
    
    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      
      const blob = new Blob([bytes], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (audioQueueRef.current.length === 0) {
          setState(s => ({ ...s, isSpeaking: false, status: 'idle' }));
        }
      };
      
      audio.play().catch(() => {});
      setState(s => ({ ...s, isSpeaking: true, status: 'speaking' }));
    } catch (e) {
      console.error('Audio playback error:', e);
    }
  }, []);

  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      mediaStreamRef.current = stream;
      const ctx = new AudioContext({ sampleRate: 16000 });
      const source = ctx.createMediaStreamSource(stream);
      
      const bufferSize = 512;
      const processor = ctx.createScriptProcessor(bufferSize, 1, 1);
      
      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        
        const inputData = e.inputBuffer.getChannelData(0);
        const int16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }
        
        wsRef.current.send(int16Data.buffer);
      };
      
      source.connect(processor);
      processor.connect(ctx.destination);
      processorRef.current = processor;
      
      setState(s => ({ ...s, isListening: true, status: 'idle', error: null }));
      
    } catch (err) {
      setState(s => ({ ...s, error: 'Microphone access denied', status: 'error' }));
    }
  }, []);

  const stopListening = useCallback(() => {
    processorRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    processorRef.current = null;
    mediaStreamRef.current = null;
    setState(s => ({ ...s, isListening: false }));
  }, []);

  const speakWithBrowserTTS = useCallback((text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.1;
      utterance.pitch = 0.9;
      
      const voices = speechSynthesis.getVoices();
      const jarvisVoice = voices.find(v => 
        v.name.includes('Daniel') || 
        v.name.includes('Google UK English Male') ||
        (v.name.includes('Samantha') === false && v.lang === 'en-GB')
      );
      if (jarvisVoice) utterance.voice = jarvisVoice;
      
      utterance.onstart = () => setState(s => ({ ...s, isSpeaking: true, status: 'speaking' }));
      utterance.onend = () => setState(s => ({ ...s, isSpeaking: false, status: 'idle' }));
      
      speechSynthesis.cancel();
      speechSynthesis.speak(utterance);
    }
  }, []);

  const playActivationSound = useCallback(() => {
    try {
      const ctx = getAudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.1);
      
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.15);
    } catch (e) {}
  }, [getAudioContext]);

  const connect = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/voice`);
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = () => {
      console.log('Voice WS connected');
      startListening();
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'status':
          setState(s => ({ ...s, status: data.state || 'idle' }));
          break;
          
        case 'wake_word':
          setState(s => ({
            ...s,
            status: 'wake',
            responseText: data.message || 'Yes, sir?'
          }));
          playActivationSound();
          break;
          
        case 'transcript':
          setState(s => ({ ...s, transcript: data.text, status: 'processing' }));
          break;
          
        case 'llm_token':
          setState(s => ({ ...s, responseText: s.responseText + data.text }));
          break;
          
        case 'tts_chunk':
          if (data.done) {
            setState(s => ({ ...s, isSpeaking: false, status: 'idle' }));
          } else {
            queueAudioChunk(data.audio);
          }
          break;
          
        case 'tts_fallback':
          speakWithBrowserTTS(data.text);
          break;
          
        case 'error':
          setState(s => ({ ...s, error: data.message, status: 'error' }));
          break;
      }
    };
    
    ws.onerror = () => {
      setState(s => ({ ...s, error: 'Voice connection error', status: 'error' }));
    };
    
    ws.onclose = () => {
      setState(s => ({ ...s, isListening: false, status: 'idle' }));
    };
    
    wsRef.current = ws;
  }, [startListening, queueAudioChunk, speakWithBrowserTTS, playActivationSound]);

  const disconnect = useCallback(() => {
    stopListening();
    wsRef.current?.close();
    wsRef.current = null;
  }, [stopListening]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    startListening,
    stopListening
  };
}
