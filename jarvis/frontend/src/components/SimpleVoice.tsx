import { useState, useRef } from 'react';
import { Mic, Send, Loader2 } from 'lucide-react';

export function SimpleVoice() {
  const [text, setText] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const sendCommand = async (inputText: string) => {
    if (!inputText.trim()) return;
    setLoading(true);
    setResponse('');

    try {
      const res = await fetch('/api/voice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText.trim() })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      console.log('[VOICE] Response:', data);
      setResponse(data.response);

      // Play audio if available
      if (data.has_audio && data.audio_b64) {
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_b64}`);
        audioRef.current = audio;
        audio.play().catch(() => {
          // Autoplay blocked, ignore
        });
      } else {
        // Fallback: browser TTS
        const u = new SpeechSynthesisUtterance(data.response);
        u.rate = 1.0; u.pitch = 0.9;
        const voices = speechSynthesis.getVoices();
        const v = voices.find(v => v.name.includes('Daniel') || v.name.includes('Google UK English Male'));
        if (v) u.voice = v;
        speechSynthesis.speak(u);
      }
    } catch (e: any) {
      console.error('[VOICE] Error:', e);
      setResponse(`Error: ${e.message}`);
    } finally {
      setLoading(false);
      setText('');
    }
  };

  // Simple voice recording
  const toggleRecord = async () => {
    if (recording) {
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        // For now, just tell user to type — STT needs file upload endpoint
        setResponse("Voice recorded. Type your command for now — STT file upload coming next.");
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorder.start();
      setRecording(true);
      setTimeout(() => { if (mediaRecorder.state === 'recording') mediaRecorder.stop(); setRecording(false); }, 5000);
    } catch (e) {
      setResponse("Microphone access denied. Check browser permissions.");
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto p-4 space-y-4 font-mono">
      {/* Response Box */}
      {response && (
        <div className={`p-3 rounded-lg border text-sm ${response.startsWith('Error') || response.startsWith('[') ? 'bg-red-900/20 border-red-800/30 text-red-300' : 'bg-blue-900/20 border-blue-800/30 text-blue-100'}`}>
          {response}
        </div>
      )}

      {/* Input Bar */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleRecord}
          className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition ${recording ? 'bg-red-600 animate-pulse' : 'bg-slate-800 hover:bg-slate-700 border border-slate-700'}`}
        >
          <Mic className={`w-4 h-4 ${recording ? 'text-white' : 'text-slate-400'}`} />
        </button>

        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') sendCommand(text); }}
          placeholder="// Type a command, sir..."
          className="flex-1 bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-cyan-100 placeholder-slate-600 focus:ring-1 focus:ring-cyan-500 outline-none"
        />

        <button
          onClick={() => sendCommand(text)}
          disabled={loading || !text.trim()}
          className="shrink-0 w-10 h-10 rounded-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 flex items-center justify-center transition"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>

      <div className="text-[10px] text-slate-600 text-center">
        Press Enter to send • Hold mic button to record (5s max)
      </div>
    </div>
  );
}
