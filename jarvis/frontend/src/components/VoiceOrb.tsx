/**
 * J.A.R.V.I.S. Voice Orb v2.1
 * 3D reactor orb with Push-to-Talk indicator, memory status, and state colors.
 */
import { useEffect, useRef, useMemo } from 'react';
import { useVoice } from '../hooks/useVoice';
import { Mic, MicOff, Trash2, Zap } from 'lucide-react';

interface VoiceOrbProps {
  size?: number;
}

export function VoiceOrb({ size = 200 }: VoiceOrbProps) {
  const {
    status,
    isSpeaking,
    isPushToTalk,
    transcript,
    responseText,
    apiStatus,
    memoryCount,
    clearMemory
  } = useVoice();
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  const theme = useMemo(() => {
    switch (status) {
      case 'wake': return { core: '#60a5fa', glow: '#3b82f6', ring: '#93c5fd', speed: 3 };
      case 'listening':
      case 'push_to_talk': return { core: '#34d399', glow: '#10b981', ring: '#6ee7b7', speed: 2 };
      case 'speaking': return { core: '#f472b6', glow: '#ec4899', ring: '#f9a8d4', speed: 4 };
      case 'processing': return { core: '#fbbf24', glow: '#f59e0b', ring: '#fcd34d', speed: 2.5 };
      case 'error': return { core: '#f87171', glow: '#ef4444', ring: '#fca5a5', speed: 1 };
      default: return { core: '#22d3ee', glow: '#06b6d4', ring: '#67e8f9', speed: 0.5 };
    }
  }, [status]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const maxR = size * 0.4;

    const draw = () => {
      timeRef.current += 0.016 * theme.speed;
      const t = timeRef.current;
      ctx.clearRect(0, 0, size, size);

      if (isPushToTalk) {
        ctx.beginPath();
        ctx.arc(cx, cy, maxR + 20 + Math.sin(t * 5) * 5, 0, Math.PI * 2);
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.setLineDash([10, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      for (let i = 3; i >= 0; i--) {
        const r = maxR + i * 15 + Math.sin(t + i) * 5;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r + 30);
        g.addColorStop(0, theme.glow + '20');
        g.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.fill();
      }

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(t * 0.5);
      for (let i = 0; i < 3; i++) {
        ctx.rotate((Math.PI * 2) / 3);
        ctx.beginPath();
        ctx.arc(0, 0, maxR + 8, -0.3, 0.3);
        ctx.strokeStyle = theme.ring + '60';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.restore();

      const pulse = status === 'idle' ? 1 + Math.sin(t * 2) * 0.05
        : status === 'wake' ? 1 + Math.sin(t * 8) * 0.15
        : 1 + Math.sin(t * 4) * 0.08;
      const cr = maxR * 0.5 * pulse;

      const cg = ctx.createRadialGradient(cx - cr * 0.3, cy - cr * 0.3, 0, cx, cy, cr);
      cg.addColorStop(0, '#ffffff');
      cg.addColorStop(0.3, theme.core);
      cg.addColorStop(0.7, theme.glow);
      cg.addColorStop(1, theme.glow + '00');
      ctx.beginPath();
      ctx.arc(cx, cy, cr, 0, Math.PI * 2);
      ctx.fillStyle = cg;
      ctx.fill();

      if (status === 'speaking' || status === 'listening' || status === 'push_to_talk') {
        const bars = 12;
        for (let i = 0; i < bars; i++) {
          const angle = (i / bars) * Math.PI * 2 + t * 0.3;
          const bh = 10 + Math.sin(t * 3 + i * 0.8) * 15 + Math.random() * 5;
          const x1 = cx + Math.cos(angle) * maxR * 0.75;
          const y1 = cy + Math.sin(angle) * maxR * 0.75;
          const x2 = cx + Math.cos(angle) * (maxR * 0.75 + bh);
          const y2 = cy + Math.sin(angle) * (maxR * 0.75 + bh);
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = theme.ring + 'aa';
          ctx.lineWidth = 3;
          ctx.lineCap = 'round';
          ctx.stroke();
        }
      }

      const particles = status === 'idle' ? 8 : 20;
      for (let i = 0; i < particles; i++) {
        const angle = (i / particles) * Math.PI * 2 + t * (0.2 + i * 0.01);
        const dist = maxR * 0.6 + Math.sin(t + i) * 10;
        ctx.beginPath();
        ctx.arc(cx + Math.cos(angle) * dist, cy + Math.sin(angle) * dist, 1 + Math.sin(t * 2 + i) * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = theme.ring + (status === 'idle' ? '40' : '80');
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [size, status, theme, isPushToTalk]);

  const statusText = {
    idle: 'Say "Hey Jarvis" or hold Space',
    wake: 'Yes, sir?',
    listening: 'Listening...',
    push_to_talk: 'Recording... (release Space)',
    processing: 'Processing...',
    speaking: 'Speaking...',
    error: 'Error'
  }[status] || 'J.A.R.V.I.S.';

  const hasAnyKey = apiStatus.stt || apiStatus.llm || apiStatus.tts;
  const usingFallback = !apiStatus.tts && status !== 'idle';

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex items-center gap-2 text-[10px] font-mono tracking-wider">
        {!hasAnyKey && (
          <span className="px-2 py-0.5 rounded-full bg-amber-900/40 border border-amber-700/30 text-amber-400 flex items-center gap-1">
            <Zap className="w-3 h-3" /> ZERO-KEY MODE
          </span>
        )}
        {usingFallback && (
          <span className="px-2 py-0.5 rounded-full bg-blue-900/40 border border-blue-700/30 text-blue-400">
            BROWSER TTS
          </span>
        )}
        {memoryCount > 0 && (
          <button
            onClick={clearMemory}
            className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-red-400 hover:border-red-700/30 transition flex items-center gap-1"
            title="Clear conversation memory"
          >
            <Trash2 className="w-3 h-3" /> {memoryCount}
          </button>
        )}
      </div>

      <div className="relative">
        <canvas
          ref={canvasRef}
          width={size}
          height={size}
          className="cursor-pointer transition-transform hover:scale-105"
          style={{ width: size, height: size }}
        />
        
        {isPushToTalk && (
          <div className="absolute -top-2 left-1/2 -translate-x-1/2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full animate-pulse">
            ● REC
          </div>
        )}
        
        <div className={`
          absolute -bottom-2 left-1/2 -translate-x-1/2 
          px-3 py-1 rounded-full text-xs font-mono tracking-wider
          border backdrop-blur-md transition-all duration-300
          ${status === 'idle' ? 'bg-slate-900/60 border-cyan-500/30 text-cyan-400' : ''}
          ${status === 'wake' ? 'bg-blue-900/60 border-blue-500/30 text-blue-400 scale-110' : ''}
          ${status === 'listening' || status === 'push_to_talk' ? 'bg-emerald-900/60 border-emerald-500/30 text-emerald-400' : ''}
          ${status === 'speaking' ? 'bg-pink-900/60 border-pink-500/30 text-pink-400' : ''}
          ${status === 'processing' ? 'bg-amber-900/60 border-amber-500/30 text-amber-400' : ''}
          ${status === 'error' ? 'bg-red-900/60 border-red-500/30 text-red-400' : ''}
        `}>
          {status === 'push_to_talk' ? <Mic className="w-3 h-3 inline mr-1" /> : null}
          {status === 'idle' ? <MicOff className="w-3 h-3 inline mr-1" /> : null}
          {statusText}
        </div>
      </div>

      <div className="max-w-sm w-full space-y-2">
        {transcript && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">You</p>
            <p className="text-sm text-slate-300">{transcript}</p>
          </div>
        )}
        {responseText && (
          <div className="bg-blue-900/20 border border-blue-800/30 rounded-lg p-3">
            <p className="text-[10px] text-blue-400 uppercase tracking-wider mb-1">J.A.R.V.I.S.</p>
            <p className="text-sm text-blue-100">{responseText}</p>
          </div>
        )}
      </div>

      <div className="text-[10px] text-slate-600 font-mono text-center space-y-0.5">
        <p>Hold <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">Space</kbd> to talk</p>
        <p>Or say <span className="text-cyan-500">"Hey Jarvis"</span></p>
      </div>
    </div>
  );
}
