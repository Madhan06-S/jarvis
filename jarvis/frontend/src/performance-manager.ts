/**
 * J.A.R.V.I.S Performance Manager — adaptive rendering, FPS telemetry, quality modes.
 */

export type QualityMode = 'ultra' | 'balanced' | 'performance';

export interface RenderProfile {
  particleCount: number;
  particleLinks: boolean;
  hexNodes: number;
  shards: number;
  dnaStrands: boolean;
  scanLine: boolean;
  shadowBlur: boolean;
  connectionDistance: number;
  targetFps: number;
  skipFrames: number;
}

const PROFILES: Record<QualityMode, RenderProfile> = {
  ultra: {
    particleCount: 100,
    particleLinks: true,
    hexNodes: 22,
    shards: 18,
    dnaStrands: true,
    scanLine: true,
    shadowBlur: true,
    connectionDistance: 80,
    targetFps: 60,
    skipFrames: 0,
  },
  balanced: {
    particleCount: 60,
    particleLinks: true,
    hexNodes: 14,
    shards: 10,
    dnaStrands: true,
    scanLine: true,
    shadowBlur: false,
    connectionDistance: 65,
    targetFps: 45,
    skipFrames: 0,
  },
  performance: {
    particleCount: 28,
    particleLinks: false,
    hexNodes: 8,
    shards: 4,
    dnaStrands: false,
    scanLine: false,
    shadowBlur: false,
    connectionDistance: 50,
    targetFps: 30,
    skipFrames: 1,
  },
};

export interface PerfSnapshot {
  fps: number;
  frameMs: number;
  mode: QualityMode;
  particles: number;
  wsPerSec: number;
  memoryMb: number | null;
  gpuTier: string;
  paused: boolean;
}

type PerfListener = (snap: PerfSnapshot) => void;

export class PerformanceManager {
  private mode: QualityMode = 'balanced';
  private manualLock = false;
  private fps = 60;
  private frameMs = 16;
  private frameCount = 0;
  private lastFpsTick = performance.now();
  private rafId: number | null = null;
  private visible = true;
  private paused = false;
  private wsCount = 0;
  private wsPerSec = 0;
  private lastWsTick = performance.now();
  private listeners: PerfListener[] = [];
  private particleCount = PROFILES.balanced.particleCount;
  private lowFpsStreak = 0;
  private highFpsStreak = 0;

  constructor() {
    this.mode = this.detectInitialMode();
    this.particleCount = PROFILES[this.mode].particleCount;

    document.addEventListener('visibilitychange', () => {
      this.visible = document.visibilityState === 'visible';
      if (!this.visible) this.pauseAnimations();
      else this.resumeAnimations();
    });

    this.bindHudControls();
    this.startLoop();
  }

  private detectInitialMode(): QualityMode {
    const cores = navigator.hardwareConcurrency || 4;
    const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return 'performance';
    if (cores >= 8 && mem >= 8) return 'ultra';
    if (cores >= 4 && mem >= 4) return 'balanced';
    return 'performance';
  }

  getGpuTier(): string {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) return 'UNKNOWN';
      const dbg = (gl as WebGLRenderingContext).getExtension('WEBGL_debug_renderer_info');
      if (dbg) {
        const renderer = (gl as WebGLRenderingContext).getParameter(dbg.UNMASKED_RENDERER_WEBGL);
        if (/swiftshader|llvmpipe|basic render/i.test(renderer)) return 'SOFTWARE';
        if (/intel/i.test(renderer)) return 'INTEGRATED';
        if (/nvidia|amd|radeon|apple m/i.test(renderer)) return 'DEDICATED';
      }
    } catch {
      /* ignore */
    }
    return 'STANDARD';
  }

  getProfile(): RenderProfile {
    return { ...PROFILES[this.mode] };
  }

  getMode(): QualityMode {
    return this.mode;
  }

  setMode(mode: QualityMode, manual = true) {
    this.mode = mode;
    if (manual) this.manualLock = true;
    this.particleCount = PROFILES[mode].particleCount;
    this.notify();
    this.updateModeBadge();
  }

  recordFrame(deltaMs: number) {
    this.frameCount++;
    this.frameMs = this.frameMs * 0.9 + deltaMs * 0.1;
    const now = performance.now();
    if (now - this.lastFpsTick >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / (now - this.lastFpsTick));
      this.frameCount = 0;
      this.lastFpsTick = now;
      if (!this.manualLock) this.autoAdjustQuality();
      this.notify();
    }
  }

  recordWsMessage() {
    this.wsCount++;
    const now = performance.now();
    if (now - this.lastWsTick >= 1000) {
      this.wsPerSec = this.wsCount;
      this.wsCount = 0;
      this.lastWsTick = now;
    }
  }

  setActiveParticles(n: number) {
    this.particleCount = n;
  }

  shouldRenderFrame(frameIndex: number): boolean {
    if (this.paused || !this.visible) return false;
    const skip = PROFILES[this.mode].skipFrames;
    return skip === 0 || frameIndex % (skip + 1) === 0;
  }

  isPaused(): boolean {
    return this.paused;
  }

  isVisible(): boolean {
    return this.visible;
  }

  onUpdate(fn: PerfListener) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn);
    };
  }

  pauseAnimations() {
    this.paused = true;
    document.body.classList.add('perf-paused');
  }

  resumeAnimations() {
    this.paused = false;
    document.body.classList.remove('perf-paused');
  }

  getSnapshot(): PerfSnapshot {
    const mem = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
    return {
      fps: this.fps,
      frameMs: Math.round(this.frameMs * 10) / 10,
      mode: this.mode,
      particles: this.particleCount,
      wsPerSec: this.wsPerSec,
      memoryMb: mem ? Math.round(mem.usedJSHeapSize / 1048576) : null,
      gpuTier: this.getGpuTier(),
      paused: this.paused,
    };
  }

  private autoAdjustQuality() {
    if (this.fps < 28) {
      this.lowFpsStreak++;
      this.highFpsStreak = 0;
    } else if (this.fps > 52) {
      this.highFpsStreak++;
      this.lowFpsStreak = 0;
    } else {
      this.lowFpsStreak = Math.max(0, this.lowFpsStreak - 1);
      this.highFpsStreak = Math.max(0, this.highFpsStreak - 1);
    }

    if (this.lowFpsStreak >= 3) {
      if (this.mode === 'ultra') this.setMode('balanced', false);
      else if (this.mode === 'balanced') this.setMode('performance', false);
      this.lowFpsStreak = 0;
    } else if (this.highFpsStreak >= 8 && this.mode === 'performance') {
      this.setMode('balanced', false);
      this.highFpsStreak = 0;
    } else if (this.highFpsStreak >= 12 && this.mode === 'balanced') {
      const cores = navigator.hardwareConcurrency || 4;
      if (cores >= 6) this.setMode('ultra', false);
      this.highFpsStreak = 0;
    }
  }

  private startLoop() {
    const tick = () => {
      this.rafId = requestAnimationFrame(tick);
    };
    tick();
  }

  private notify() {
    const snap = this.getSnapshot();
    this.listeners.forEach((fn) => fn(snap));
  }

  private updateModeBadge() {
    const el = document.getElementById('perf-mode-val');
    if (el) el.textContent = this.mode.toUpperCase();
  }

  private bindHudControls() {
    const select = document.getElementById('perf-mode-select') as HTMLSelectElement | null;
    if (select) {
      select.value = this.mode;
      select.addEventListener('change', () => {
        this.setMode(select.value as QualityMode, true);
      });
    }
    this.updateModeBadge();

    this.onUpdate((snap) => {
      const set = (id: string, val: string) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };
      set('perf-fps', String(snap.fps));
      set('perf-frame-ms', `${snap.frameMs}ms`);
      set('perf-mode-val', snap.mode.toUpperCase());
      set('perf-particles', String(snap.particles));
      set('perf-ws-rate', `${snap.wsPerSec}/s`);
      set('perf-gpu-tier', snap.gpuTier);
      if (snap.memoryMb !== null) set('perf-mem', `${snap.memoryMb} MB`);

      const fpsBar = document.getElementById('perf-fps-bar') as HTMLElement | null;
      if (fpsBar) {
        const pct = Math.min(100, (snap.fps / 60) * 100);
        fpsBar.style.width = `${pct}%`;
        fpsBar.style.background =
          snap.fps < 30 ? '#ff3300' : snap.fps < 45 ? '#ff8c00' : '#00ff88';
      }

      const cpuBar = document.getElementById('cpu-bar');
      const cpuVal = document.getElementById('cpu-val');
      const memBar = document.getElementById('mem-bar');
      const memVal = document.getElementById('mem-val');
      const load = Math.min(95, Math.round(100 - snap.fps * 1.2 + snap.frameMs * 2));
      const memPct = snap.memoryMb
        ? Math.min(90, Math.round((snap.memoryMb / 512) * 100))
        : Math.round(40 + snap.frameMs);
      if (cpuBar) (cpuBar as HTMLElement).style.width = `${load}%`;
      if (cpuVal) cpuVal.textContent = `${load}%`;
      if (memBar) (memBar as HTMLElement).style.width = `${memPct}%`;
      if (memVal) memVal.textContent = `${memPct}%`;

      const pCount = document.getElementById('p-count');
      if (pCount) pCount.textContent = String(snap.particles);
    });
  }

  destroy() {
    if (this.rafId) cancelAnimationFrame(this.rafId);
  }
}

let instance: PerformanceManager | null = null;

export function getPerformanceManager(): PerformanceManager {
  if (!instance) instance = new PerformanceManager();
  return instance;
}
