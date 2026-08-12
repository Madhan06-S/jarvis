/**
 * J.A.R.V.I.S. Voice Orb v2.0
 * 3D glowing reactor orb with state-aware animations.
 * States: idle (slow pulse) → wake (bright flash) → listening (active ring) → speaking (frequency bars)
 */
import { useEffect, useRef, useMemo } from 'react';
import { useVoice } from '../hooks/useVoice';

interface VoiceOrbProps {
  size?: number;
}

export function VoiceOrb({ size = 200 }: VoiceOrbProps) {
  const { status, transcript, responseText } = useVoice();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  const theme = useMemo(() => {
    switch (status) {
      case 'wake':
        return { core: '#60a5fa', glow: '#3b82f6', ring: '#93c5fd', speed: 3 };
      case 'listening':
        return { core: '#34d399', glow: '#10b981', ring: '#6ee7b7', speed: 2 };
      case 'speaking':
        return { core: '#f472b6', glow: '#ec4899', ring: '#f9a8d4', speed: 4 };
      case 'processing':
        return { core: '#fbbf24', glow: '#f59e0b', ring: '#fcd34d', speed: 2.5 };
      case 'error':
        return { core: '#f87171', glow: '#ef4444', ring: '#fca5a5', speed: 1 };
      default: // idle
        return { core: '#22d3ee', glow: '#06b6d4', ring: '#67e8f9', speed: 0.5 };
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

    const centerX = size / 2;
    const centerY = size / 2;
    const maxRadius = size * 0.4;

    const draw = () => {
      timeRef.current += 0.016 * theme.speed;
      const t = timeRef.current;

      ctx.clearRect(0, 0, size, size);

      // Outer glow rings
      for (let i = 3; i >= 0; i--) {
        const radius = maxRadius + i * 15 + Math.sin(t + i) * 5;
        const alpha = 0.08 - i * 0.015;
        
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius + 30);
        gradient.addColorStop(0, theme.glow + Math.floor(alpha * 255).toString(16).padStart(2, '0'));
        gradient.addColorStop(1, 'transparent');
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      // Rotating ring segments
      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(t * 0.5);
      
      for (let i = 0; i < 3; i++) {
        ctx.rotate((Math.PI * 2) / 3);
        ctx.beginPath();
        ctx.arc(0, 0, maxRadius + 8, -0.3, 0.3);
        ctx.strokeStyle = theme.ring + '60';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.restore();

      // Core orb
      const pulseScale = status === 'idle' 
        ? 1 + Math.sin(t * 2) * 0.05
        : status === 'wake'
        ? 1 + Math.sin(t * 8) * 0.15
        : 1 + Math.sin(t * 4) * 0.08;

      const coreRadius = maxRadius * 0.5 * pulseScale;
      
      const coreGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, coreRadius * 2);
      coreGlow.addColorStop(0, theme.core + 'ff');
      coreGlow.addColorStop(0.4, theme.glow + '80');
      coreGlow.addColorStop(1, 'transparent');
      
      ctx.beginPath();
      ctx.arc(centerX, centerY, coreRadius * 2, 0, Math.PI * 2);
      ctx.fillStyle = coreGlow;
      ctx.fill();

      const coreGrad = ctx.createRadialGradient(
        centerX - coreRadius * 0.3, centerY - coreRadius * 0.3, 0,
        centerX, centerY, coreRadius
      );
      coreGrad.addColorStop(0, '#ffffff');
      coreGrad.addColorStop(0.3, theme.core);
      coreGrad.addColorStop(0.7, theme.glow);
      coreGrad.addColorStop(1, theme.glow + '00');

      ctx.beginPath();
      ctx.arc(centerX, centerY, coreRadius, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Frequency bars when speaking or listening
      if (status === 'speaking' || status === 'listening') {
        const bars = 12;
        const barWidth = 3;
        const barRadius = maxRadius * 0.75;
        
        for (let i = 0; i < bars; i++) {
          const angle = (i / bars) * Math.PI * 2 + t * 0.3;
          const barHeight = 10 + Math.sin(t * 3 + i * 0.8) * 15 + Math.random() * 5;
          
          const x1 = centerX + Math.cos(angle) * barRadius;
          const y1 = centerY + Math.sin(angle) * barRadius;
          const x2 = centerX + Math.cos(angle) * (barRadius + barHeight);
          const y2 = centerY + Math.sin(angle) * (barRadius + barHeight);
          
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = theme.ring + 'aa';
          ctx.lineWidth = barWidth;
          ctx.lineCap = 'round';
          ctx.stroke();
        }
      }

      // Particles
      const particles = status === 'idle' ? 8 : 20;
      for (let i = 0; i < particles; i++) {
        const angle = (i / particles) * Math.PI * 2 + t * (0.2 + i * 0.01);
        const dist = maxRadius * 0.6 + Math.sin(t + i) * 10;
        const px = centerX + Math.cos(angle) * dist;
        const py = centerY + Math.sin(angle) * dist;
        const pSize = 1 + Math.sin(t * 2 + i) * 0.5;
        
        ctx.beginPath();
        ctx.arc(px, py, pSize, 0, Math.PI * 2);
        ctx.fillStyle = theme.ring + (status === 'idle' ? '40' : '80');
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [size, status, theme]);

  const statusText = {
    idle: 'Say "Hey Jarvis"',
    wake: 'Yes, sir?',
    listening: 'Listening...',
    processing: 'Processing...',
    speaking: 'Speaking...',
    error: 'Error'
  }[status] || 'J.A.R.V.I.S.';

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={size}
          height={size}
          className="cursor-pointer transition-transform hover:scale-105"
          style={{ width: size, height: size }}
        />
        
        <div 
          className={`
            absolute -bottom-2 left-1/2 -translate-x-1/2 
            px-3 py-1 rounded-full text-xs font-mono tracking-wider
            border backdrop-blur-md transition-all duration-300
            ${status === 'idle' ? 'bg-slate-900/60 border-cyan-500/30 text-cyan-400' : ''}
            ${status === 'wake' ? 'bg-blue-900/60 border-blue-500/30 text-blue-400 scale-110' : ''}
            ${status === 'listening' ? 'bg-emerald-900/60 border-emerald-500/30 text-emerald-400' : ''}
            ${status === 'speaking' ? 'bg-pink-900/60 border-pink-500/30 text-pink-400' : ''}
            ${status === 'processing' ? 'bg-amber-900/60 border-amber-500/30 text-amber-400' : ''}
            ${status === 'error' ? 'bg-red-900/60 border-red-500/30 text-red-400' : ''}
          `}
        >
          {statusText}
        </div>
      </div>
      
      <div className="max-w-md text-center space-y-1">
        {transcript && <p className="text-xs text-cyan-300 font-mono italic">"{transcript}"</p>}
        {responseText && <p className="text-xs text-slate-300 font-mono">{responseText}</p>}
      </div>
    </div>
  );
}
