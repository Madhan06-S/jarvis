import { useState, useRef, useEffect } from 'react';
import { Mic, Send, Loader2, Activity, Wifi, WifiOff } from 'lucide-react';

export function JarvisInput() {
  const [text, setText] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addLog = (msg: string) => {
    console.log(`[JARVIS] ${msg}`);
    setLogs(prev => [...prev.slice(-9), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  // Test backend connection on mount
  useEffect(() => {
    testBackend();
  }, []);

  const testBackend = async () => {
    addLog('Testing backend connection...');
    try {
      const res = await fetch('/api/voice/health', { method: 'GET' });
      const data = await res.json();
      addLog(`Backend OK: ${JSON.stringify(data)}`);
      setBackendOk(true);
    } catch (e: any) {
      addLog(`Backend FAILED: ${e.message}`);
      setBackendOk(false);
    }
  };

  const send = async () => {
    const cmd = text.trim();
    if (!cmd) {
      addLog('Empty input, ignoring');
      return;
    }

    setLoading(true);
    setResponse('');
    addLog(`Sending: "${cmd}"`);

    try {
      addLog('Fetching /api/voice/command...');
      const res = await fetch('/api/voice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cmd })
      });

      addLog(`Response status: ${res.status}`);

      if (!res.ok) {
        const errText = await res.text();
        addLog(`HTTP Error ${res.status}: ${errText}`);
        setResponse(`[HTTP ${res.status}] ${errText}`);
        setLoading(false);
        return;
      }

      const data = await res.json();
      addLog(`Got data: ${JSON.stringify(data).substring(0, 120)}`);

      if (data.response) {
        setResponse(data.response);
        addLog(`Response: ${data.response.substring(0, 50)}...`);

        // Browser TTS fallback
        if ('speechSynthesis' in window) {
          const u = new SpeechSynthesisUtterance(data.response);
          u.rate = 1.0; u.pitch = 0.9;
          const voices = speechSynthesis.getVoices();
          const v = voices.find(v => v.name.includes('Daniel') || v.name.includes('Google UK English Male'));
          if (v) u.voice = v;
          speechSynthesis.cancel();
          speechSynthesis.speak(u);
          addLog('Browser TTS speaking');
        }

        // Play ElevenLabs audio if available
        if (data.has_audio && data.audio_b64) {
          const audio = new Audio(`data:audio/mpeg;base64,${data.audio_b64}`);
          audio.play().catch(() => addLog('Audio autoplay blocked'));
        }
      } else {
        setResponse('[No response field in data]');
        addLog('No response field');
      }

    } catch (e: any) {
      addLog(`Fetch ERROR: ${e.message}`);
      setResponse(`[Network Error] ${e.message}. Is backend running on port 8340?`);
    } finally {
      setLoading(false);
      setText('');
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addLog('Enter pressed');
      send();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 flex flex-col items-center pb-6 pt-2 px-4"
         style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, transparent 100%)' }}>
      
      {/* Debug Panel */}
      <div className="mb-2 w-full max-w-2xl">
        {/* Connection Status */}
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            {backendOk === true && <Wifi className="w-3 h-3 text-emerald-400" />}
            {backendOk === false && <WifiOff className="w-3 h-3 text-red-400" />}
            {backendOk === null && <Activity className="w-3 h-3 text-amber-400 animate-pulse" />}
            <span className="text-[10px] font-mono tracking-wider"
                  style={{ color: backendOk === true ? '#34d399' : backendOk === false ? '#f87171' : '#fbbf24' }}>
              {backendOk === true ? 'BACKEND ONLINE' : backendOk === false ? 'BACKEND OFFLINE' : 'CHECKING...'}
            </span>
            <button onClick={testBackend} 
                    className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 hover:text-cyan-400">
              RETEST
            </button>
          </div>
          <button onClick={() => setLogs([])} className="text-[9px] text-slate-600 hover:text-slate-400">
            CLEAR LOGS
          </button>
        </div>

        {/* Logs */}
        {logs.length > 0 && (
          <div className="mb-2 p-2 rounded-lg bg-black/60 border border-slate-800/50 font-mono text-[9px] leading-tight max-h-24 overflow-y-auto">
            {logs.map((l, i) => (
              <div key={i} className={l.includes('ERROR') || l.includes('FAILED') ? 'text-red-400' : 'text-slate-500'}>
                {l}
              </div>
            ))}
          </div>
        )}

        {/* Response */}
        {response && (
          <div className={`mb-2 p-3 rounded-lg border text-sm font-mono leading-relaxed
            ${response.startsWith('[') || response.startsWith('Error') 
              ? 'bg-red-900/20 border-red-800/30 text-red-300' 
              : 'bg-cyan-900/10 border-cyan-800/20 text-cyan-100'}`}>
            {response}
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="flex items-center gap-3 w-full max-w-2xl">
        {/* Mic Button */}
        <button className="shrink-0 w-11 h-11 rounded-full flex items-center justify-center
                           bg-slate-900/80 border border-cyan-500/30 text-cyan-400
                           hover:bg-cyan-900/30 hover:border-cyan-400/50 transition-all">
          <Mic className="w-4 h-4" />
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="// Type a command, sir..."
            className="w-full bg-slate-950/80 border border-cyan-500/20 rounded-xl 
                       px-5 py-3 text-sm text-cyan-100 placeholder-cyan-800/60 
                       font-mono tracking-wide
                       focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-500/20
                       disabled:opacity-50"
            style={{ backdropFilter: 'blur(12px)' }}
          />
          {loading && (
            <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-cyan-400 animate-spin" />
          )}
        </div>

        {/* Send Button */}
        <button
          onClick={() => { addLog('Send button clicked'); send(); }}
          disabled={loading || !text.trim()}
          className="shrink-0 w-11 h-11 rounded-full flex items-center justify-center
                     bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600
                     text-white transition-all shadow-lg shadow-cyan-500/20">
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
