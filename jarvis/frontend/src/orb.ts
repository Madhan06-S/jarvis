import { getPerformanceManager, type RenderProfile } from './performance-manager';

export type OrbState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'executing' | 'speaking';

export interface ReactorProps {
  style: 'ring' | 'sphere' | 'wire';
  scale: number;
  intensity: number;
  spin: number;
  color: string | null;
  visible: boolean;
}

export interface OrbitDef {
  id: string;
  src: string;
  radius?: number;
  speed?: number;
  size?: number;
  tilt?: number;
  opacity?: number;
  phase?: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  pulse: number;
}

interface Shard {
  x: number;
  y: number;
  vx: number;
  vy: number;
  w: number;
  h: number;
  rot: number;
  rotSpeed: number;
  alpha: number;
}

interface HexNode {
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  angle: number;
  speed: number;
  amp: number;
  size: number;
  alpha: number;
  pulse: number;
}

export function createOrb(_canvas: HTMLCanvasElement) {
  const wrap = document.getElementById('jarvis-wrap')!;
  const bg = document.getElementById('bgCanvas') as HTMLCanvasElement;
  const fg = document.getElementById('fgCanvas') as HTMLCanvasElement;
  const bctx = bg.getContext('2d', { alpha: true })!;
  const fctx = fg.getContext('2d', { alpha: true })!;
  const perf = getPerformanceManager();

  let W = wrap.clientWidth;
  let H = wrap.clientHeight;
  bg.width = fg.width = W;
  bg.height = fg.height = H;
  let cx = W / 2;
  let cy = H / 2 - 30;

  let t = 0;
  const startTime = Date.now();
  let state: OrbState = 'idle';
  let analyser: AnalyserNode | null = null;
  const timeData = new Uint8Array(200);
  let frameIndex = 0;
  let animId: number | null = null;
  let running = true;

  let profile: RenderProfile = perf.getProfile();
  let particles: Particle[] = [];
  let shards: Shard[] = [];
  let hexNodes: HexNode[] = [];

  const rings = [
    { r: 38, speed: 0.018, dash: [6, 4], w: 1.2, phase: 0 },
    { r: 55, speed: -0.013, dash: [3, 7], w: 0.8, phase: 1 },
    { r: 72, speed: 0.009, dash: [12, 4, 3, 4], w: 1.0, phase: 2 },
    { r: 90, speed: -0.007, dash: [5, 15], w: 0.6, phase: 3 },
    { r: 108, speed: 0.005, dash: [20, 6], w: 0.8, phase: 4 },
    { r: 130, speed: -0.004, dash: [4, 30], w: 0.5, phase: 5 },
  ];

  const dnaCount = 40;
  const dnaPoints = Array.from({ length: dnaCount }, (_, i) => ({
    t: (i / dnaCount) * Math.PI * 4,
  }));

  let scanY = 0;
  let scanDir = 1;

  function rebuildEntities() {
    profile = perf.getProfile();
    particles = [];
    for (let i = 0; i < profile.particleCount; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.4,
        vy: -(Math.random() * 0.6 + 0.1),
        size: Math.random() * 2 + 0.3,
        alpha: Math.random() * 0.6 + 0.2,
        pulse: Math.random() * Math.PI * 2,
      });
    }

    shards = [];
    for (let i = 0; i < profile.shards; i++) {
      shards.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.25,
        vy: -(Math.random() * 0.3 + 0.05),
        w: Math.random() * 40 + 15,
        h: Math.random() * 8 + 3,
        rot: Math.random() * Math.PI,
        rotSpeed: (Math.random() - 0.5) * 0.015,
        alpha: Math.random() * 0.2 + 0.05,
      });
    }

    hexNodes = [];
    for (let i = 0; i < profile.hexNodes; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist = 80 + Math.random() * 200;
      hexNodes.push({
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        baseX: cx + Math.cos(angle) * dist,
        baseY: cy + Math.sin(angle) * dist,
        angle: Math.random() * Math.PI * 2,
        speed: 0.008 + Math.random() * 0.012,
        amp: 4 + Math.random() * 10,
        size: 2 + Math.random() * 2.5,
        alpha: 0.3 + Math.random() * 0.4,
        pulse: Math.random() * Math.PI * 2,
      });
    }

    perf.setActiveParticles(particles.length);
  }

  rebuildEntities();
  perf.onUpdate(() => {
    if (particles.length !== perf.getProfile().particleCount) rebuildEntities();
  });

  let reactor: ReactorProps = {
    style: 'ring',
    scale: 1.0,
    intensity: 1.0,
    spin: 1.0,
    color: null,
    visible: true,
  };

  interface ActiveOrbit {
    def: OrbitDef;
    img: HTMLImageElement | null;
    loaded: boolean;
    angle: number;
  }

  const activeOrbits: Map<string, ActiveOrbit> = new Map();

  function resolveOrbitSrc(src: string): string {
    const token = localStorage.getItem('jarvis_token') || '';
    const tokenQuery = token ? `&token=${encodeURIComponent(token)}` : '';
    const clean = src.replace(/^file:\/\//, '');
    if (clean.startsWith('/') || /^[a-zA-Z]:\\/.test(clean)) {
      return `/api/proxy/img?path=${encodeURIComponent(clean)}${tokenQuery}`;
    }
    if (/^https?:\/\//i.test(src)) {
      return `/api/proxy/img?url=${encodeURIComponent(src)}${tokenQuery}`;
    }
    return src;
  }

  function drawArcReactor() {
    if (!reactor.visible) return;

    let speedMult = reactor.spin;
    let colorTint = reactor.color || 'rgba(150,240,255,0.95)';
    if (!reactor.color) {
      if (state === 'listening') {
        speedMult *= 2;
        colorTint = 'rgba(0,255,200,0.95)';
      } else if (state === 'transcribing') {
        speedMult *= 2.5;
        colorTint = 'rgba(255,215,0,0.95)';
      } else if (state === 'thinking') {
        speedMult *= 3;
        colorTint = 'rgba(200,150,255,0.95)';
      } else if (state === 'executing') {
        speedMult *= 2;
        colorTint = 'rgba(0,255,136,0.95)';
      } else if (state === 'speaking') {
        speedMult *= 1.5;
      }
    }

    const sc = reactor.scale;
    const it = reactor.intensity;

    if (reactor.style === 'sphere') {
      // Solid plasma core
      const coreR = 36 * sc;
      const grd = bctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
      grd.addColorStop(0, '#ffffff');
      grd.addColorStop(0.2, colorTint);
      grd.addColorStop(0.7, 'rgba(0,180,255,0.6)');
      grd.addColorStop(1, 'rgba(0,0,0,0)');

      bctx.save();
      bctx.shadowBlur = 25 * it;
      bctx.shadowColor = colorTint;
      bctx.beginPath();
      bctx.arc(cx, cy, coreR + Math.sin(t * 4) * 2, 0, Math.PI * 2);
      bctx.fillStyle = grd;
      bctx.fill();

      // Coronal flares
      for (let i = 0; i < 4; i++) {
        bctx.beginPath();
        const a = t * (0.4 + i * 0.2) * speedMult + (i * Math.PI) / 2;
        bctx.arc(cx, cy, (coreR + 15 + i * 8) * sc, a, a + Math.PI * 0.6);
        bctx.strokeStyle = colorTint;
        bctx.lineWidth = 1.5 * sc;
        bctx.stroke();
      }
      bctx.restore();

    } else if (reactor.style === 'wire') {
      // Skeletal geodesic lattice
      const latticeR = 40 * sc;
      bctx.save();
      bctx.translate(cx, cy);
      bctx.strokeStyle = colorTint;
      bctx.lineWidth = 1;
      bctx.shadowBlur = 10 * it;
      bctx.shadowColor = colorTint;

      const angle = t * 0.7 * speedMult;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);

      // 3D Polyhedron points
      const points = [
        [-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0],
        [0, 0, -1], [0, 0, 1],
        [-0.7, -0.7, 0], [0.7, -0.7, 0], [0.7, 0.7, 0], [-0.7, 0.7, 0],
      ];

      const proj = points.map(([x, y, z]) => {
        const rx = x * cosA - z * sinA;
        const rz = x * sinA + z * cosA;
        const ry = y * Math.cos(angle * 0.8) - rz * Math.sin(angle * 0.8);
        return {
          px: rx * latticeR,
          py: ry * latticeR,
          pz: rz,
        };
      });

      bctx.beginPath();
      for (let i = 0; i < proj.length; i++) {
        for (let j = i + 1; j < proj.length; j++) {
          const d = Math.hypot(proj[i].px - proj[j].px, proj[i].py - proj[j].py);
          if (d < latticeR * 1.5) {
            bctx.moveTo(proj[i].px, proj[i].py);
            bctx.lineTo(proj[j].px, proj[j].py);
          }
        }
      }
      bctx.stroke();

      for (let i = 0; i < 24; i++) {
        const ta = (i / 24) * Math.PI * 2;
        const r1 = 55 * sc;
        const r2 = (i % 6 === 0 ? 64 : 59) * sc;
        bctx.beginPath();
        bctx.moveTo(Math.cos(ta) * r1, Math.sin(ta) * r1);
        bctx.lineTo(Math.cos(ta) * r2, Math.sin(ta) * r2);
        bctx.stroke();
      }
      bctx.restore();

    } else {
      // Stock Arc Reactor ('ring')
      const grd = bctx.createRadialGradient(cx, cy, 0, cx, cy, 30 * sc);
      grd.addColorStop(0, colorTint);
      grd.addColorStop(0.35, 'rgba(0,180,255,0.5)');
      grd.addColorStop(1, 'rgba(0,0,0,0)');
      bctx.beginPath();
      bctx.arc(cx, cy, 30 * sc, 0, Math.PI * 2);
      bctx.fillStyle = grd;
      bctx.fill();

      bctx.save();
      bctx.translate(cx, cy);
      bctx.rotate(t * 0.5 * speedMult);
      bctx.beginPath();
      for (let i = 0; i < 3; i++) {
        const a = (i / 3) * Math.PI * 2 - Math.PI / 2;
        if (i === 0) bctx.moveTo(Math.cos(a) * 16 * sc, Math.sin(a) * 16 * sc);
        else bctx.lineTo(Math.cos(a) * 16 * sc, Math.sin(a) * 16 * sc);
      }
      bctx.closePath();
      bctx.strokeStyle = `rgba(0,220,255,${(0.65 + Math.sin(t * 2) * 0.25) * it})`;
      bctx.lineWidth = 1 * sc;
      bctx.stroke();
      bctx.restore();

      const ringLimit = perf.getMode() === 'performance' ? 4 : rings.length;
      for (let i = 0; i < ringLimit; i++) {
        const ring = rings[i];
        bctx.save();
        bctx.translate(cx, cy);
        bctx.rotate(t * ring.speed * speedMult + ring.phase);
        bctx.beginPath();
        bctx.arc(0, 0, ring.r * sc, 0, Math.PI * 2);
        bctx.setLineDash(ring.dash.map((d) => d * sc));
        const alpha = (0.3 + Math.sin(t * 0.8 + ring.phase) * 0.12) * it;
        bctx.strokeStyle = `rgba(0,191,255,${alpha})`;
        bctx.lineWidth = ring.w * sc;
        bctx.stroke();
        bctx.restore();
      }
    }
  }

  function drawOrbits() {
    if (activeOrbits.size === 0) return;

    activeOrbits.forEach((entry) => {
      const def = entry.def;
      const speed = (def.speed ?? 4) * 0.015 * reactor.spin;
      entry.angle += speed;

      const r = Math.min(W, H) * (def.radius ?? 0.55) * 0.5 * reactor.scale;
      const tiltRad = ((def.tilt ?? 24) * Math.PI) / 180;

      // Draw orbit path ellipse
      bctx.save();
      bctx.translate(cx, cy);
      bctx.scale(1, Math.sin(tiltRad));
      bctx.beginPath();
      bctx.arc(0, 0, r, 0, Math.PI * 2);
      bctx.strokeStyle = 'rgba(0, 191, 255, 0.15)';
      bctx.setLineDash([4, 8]);
      bctx.stroke();
      bctx.restore();

      // 3D position
      const ox = cx + Math.cos(entry.angle) * r;
      const oy = cy + Math.sin(entry.angle) * r * Math.sin(tiltRad);
      const oz = Math.sin(entry.angle) * Math.cos(tiltRad);

      const size = (def.size ?? 96) * (0.85 + oz * 0.25) * reactor.scale;
      const opacity = (def.opacity ?? 0.9) * (0.75 + oz * 0.25) * reactor.intensity;

      bctx.save();
      bctx.globalAlpha = Math.max(0.1, Math.min(1.0, opacity));

      if (entry.loaded && entry.img) {
        bctx.save();
        bctx.beginPath();
        bctx.arc(ox, oy, size / 2, 0, Math.PI * 2);
        bctx.clip();
        bctx.drawImage(entry.img, ox - size / 2, oy - size / 2, size, size);
        bctx.restore();

        bctx.beginPath();
        bctx.arc(ox, oy, size / 2, 0, Math.PI * 2);
        bctx.strokeStyle = 'rgba(0, 191, 255, 0.7)';
        bctx.lineWidth = 1.5;
        bctx.shadowBlur = 10;
        bctx.shadowColor = '#00BFFF';
        bctx.stroke();

        bctx.font = '8px monospace';
        bctx.fillStyle = '#00BFFF';
        bctx.textAlign = 'center';
        bctx.fillText(def.id.toUpperCase(), ox, oy + size / 2 + 12);
      } else {
        bctx.strokeStyle = 'rgba(0, 191, 255, 0.4)';
        bctx.strokeRect(ox - size / 2, oy - size / 2, size, size);
      }
      bctx.restore();
    });
  }

  function drawHexNodes() {
    if (hexNodes.length < 2) return;
    const linkDist = perf.getMode() === 'performance' ? 90 : 110;
    bctx.lineWidth = 0.4;
    for (let i = 0; i < hexNodes.length; i++) {
      for (let j = i + 1; j < hexNodes.length; j++) {
        const dx = hexNodes[i].x - hexNodes[j].x;
        const dy = hexNodes[i].y - hexNodes[j].y;
        if (dx * dx + dy * dy < linkDist * linkDist) {
          const dist = Math.sqrt(dx * dx + dy * dy);
          const alpha = (1 - dist / linkDist) * 0.25;
          bctx.beginPath();
          bctx.moveTo(hexNodes[i].x, hexNodes[i].y);
          bctx.lineTo(hexNodes[j].x, hexNodes[j].y);
          bctx.strokeStyle = `rgba(0,191,255,${alpha})`;
          bctx.stroke();
        }
      }
    }

    hexNodes.forEach((n) => {
      const mult = state === 'thinking' ? 2.5 : 1;
      n.angle += n.speed * mult;
      n.x = n.baseX + Math.sin(n.angle) * n.amp;
      n.y = n.baseY + Math.cos(n.angle * 0.7) * n.amp * 0.6;
      n.pulse += 0.04;
      const alpha = n.alpha * (0.7 + Math.sin(n.pulse) * 0.25);
      bctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2 - Math.PI / 6;
        const px = n.x + Math.cos(a) * n.size;
        const py = n.y + Math.sin(a) * n.size;
        if (i === 0) bctx.moveTo(px, py);
        else bctx.lineTo(px, py);
      }
      bctx.closePath();
      bctx.strokeStyle = `rgba(0,220,255,${alpha})`;
      bctx.stroke();
    });
  }

  function drawParticlesLinked() {
    const cell = profile.connectionDistance;
    const grid = new Map<string, number[]>();

    particles.forEach((p, idx) => {
      p.x += p.vx * (state === 'thinking' ? 1.8 : 1);
      p.y += p.vy * (state === 'thinking' ? 1.8 : 1);
      p.pulse += 0.05;
      const dx = cx - p.x;
      const dy = cy - p.y;
      if (dx * dx + dy * dy > 40000) {
        p.vx += dx * 0.00006;
        p.vy += dy * 0.00006;
      }
      if (p.y < -10) p.y = H + 10;
      if (p.x < -10) p.x = W + 10;
      if (p.x > W + 10) p.x = -10;

      const gx = Math.floor(p.x / cell);
      const gy = Math.floor(p.y / cell);
      const key = `${gx},${gy}`;
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key)!.push(idx);
    });

    if (profile.particleLinks) {
      fctx.lineWidth = 0.35;
      const checked = new Set<string>();
      particles.forEach((p, i) => {
        const gx = Math.floor(p.x / cell);
        const gy = Math.floor(p.y / cell);
        for (let ox = -1; ox <= 1; ox++) {
          for (let oy = -1; oy <= 1; oy++) {
            const neighbors = grid.get(`${gx + ox},${gy + oy}`);
            if (!neighbors) continue;
            for (const j of neighbors) {
              if (j <= i) continue;
              const pair = i < j ? `${i}-${j}` : `${j}-${i}`;
              if (checked.has(pair)) continue;
              checked.add(pair);
              const o = particles[j];
              const dx = p.x - o.x;
              const dy = p.y - o.y;
              const d2 = dx * dx + dy * dy;
              const maxD = profile.connectionDistance;
              if (d2 < maxD * maxD) {
                const a = (1 - Math.sqrt(d2) / maxD) * 0.2;
                fctx.beginPath();
                fctx.moveTo(p.x, p.y);
                fctx.lineTo(o.x, o.y);
                fctx.strokeStyle = `rgba(0,150,220,${a})`;
                fctx.stroke();
              }
            }
          }
        }
      });
    }

    particles.forEach((p) => {
      const a = p.alpha * (0.6 + Math.sin(p.pulse) * 0.35);
      fctx.beginPath();
      fctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      fctx.fillStyle = `rgba(0,191,255,${a})`;
      fctx.fill();
    });
  }

  function drawShards() {
    shards.forEach((s) => {
      s.x += s.vx;
      s.y += s.vy;
      s.rot += s.rotSpeed;
      if (s.y < -30) s.y = H + 30;
      if (s.x < -60) s.x = W + 60;
      if (s.x > W + 60) s.x = -60;
      fctx.save();
      fctx.translate(s.x, s.y);
      fctx.rotate(s.rot);
      fctx.fillStyle = `rgba(0,191,255,${s.alpha})`;
      fctx.fillRect(-s.w / 2, -s.h / 2, s.w, s.h);
      fctx.restore();
    });
  }

  function drawDNA() {
    if (!profile.dnaStrands) return;
    const dnaX = W - 90;
    const dnaY = cy - 80;
    const dnaH = 160;
    fctx.lineWidth = 0.7;
    for (let i = 0; i < dnaCount - 1; i++) {
      const p1 = dnaPoints[i];
      const p2 = dnaPoints[i + 1];
      const y1 = dnaY + (i / dnaCount) * dnaH;
      const y2 = dnaY + ((i + 1) / dnaCount) * dnaH;
      const x1a = dnaX + Math.sin(p1.t + t * 0.8) * 18;
      const x1b = dnaX - Math.sin(p1.t + t * 0.8) * 18;
      const x2a = dnaX + Math.sin(p2.t + t * 0.8) * 18;
      const x2b = dnaX - Math.sin(p2.t + t * 0.8) * 18;
      fctx.beginPath();
      fctx.moveTo(x1a, y1);
      fctx.lineTo(x2a, y2);
      fctx.strokeStyle = 'rgba(0,200,255,0.45)';
      fctx.stroke();
      fctx.beginPath();
      fctx.moveTo(x1b, y1);
      fctx.lineTo(x2b, y2);
      fctx.strokeStyle = 'rgba(0,140,220,0.35)';
      fctx.stroke();
    }
  }

  function drawScanLine() {
    if (!profile.scanLine) return;
    scanY += scanDir * 1.1;
    if (scanY > H) scanDir = -1;
    if (scanY < 0) scanDir = 1;
    const grd = fctx.createLinearGradient(0, scanY - 5, 0, scanY + 5);
    grd.addColorStop(0, 'rgba(0,191,255,0)');
    grd.addColorStop(0.5, 'rgba(0,191,255,0.05)');
    grd.addColorStop(1, 'rgba(0,191,255,0)');
    fctx.fillStyle = grd;
    fctx.fillRect(0, scanY - 5, W, 10);
  }

  function drawMiniCharts() {
    const barW = 140;
    const barH = 24;
    const barX = cx - barW / 2;
    const barY = H - 55;
    fctx.strokeStyle = 'rgba(0,191,255,0.25)';
    fctx.lineWidth = 0.5;
    fctx.strokeRect(barX, barY, barW, barH);
    fctx.beginPath();
    if (analyser && state === 'speaking') {
      analyser.getByteTimeDomainData(timeData);
      for (let i = 0; i < barW; i++) {
        const index = Math.floor((i / barW) * timeData.length);
        const v = timeData[index] / 128.0;
        const y = barY + barH / 2 + v * 7;
        if (i === 0) fctx.moveTo(barX + i, y);
        else fctx.lineTo(barX + i, y);
      }
    } else {
      for (let i = 0; i <= barW; i += 2) {
        const y = barY + barH / 2 + Math.sin(i * 0.15 + t * 2.5) * 4;
        if (i === 0) fctx.moveTo(barX + i, y);
        else fctx.lineTo(barX + i, y);
      }
    }
    fctx.strokeStyle = 'rgba(0,200,255,0.55)';
    fctx.stroke();
  }

  function updateUptime() {
    const sec = Math.floor((Date.now() - startTime) / 1000);
    const h = String(Math.floor(sec / 3600)).padStart(2, '0');
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    const uEl = document.getElementById('uptime');
    if (uEl) uEl.textContent = `${h}:${m}:${s}`;
  }

  let lastFrame = performance.now();

  function frame(now: number) {
    if (!running) return;
    animId = requestAnimationFrame(frame);

    if (perf.isPaused() || !perf.isVisible()) return;

    const delta = now - lastFrame;
    lastFrame = now;
    perf.recordFrame(delta);

    frameIndex++;
    if (!perf.shouldRenderFrame(frameIndex)) return;

    t += Math.min(delta / 1000, 0.032);
    bctx.clearRect(0, 0, W, H);
    fctx.clearRect(0, 0, W, H);

    const vgrd = bctx.createRadialGradient(cx, cy, 90, cx, cy, W * 0.65);
    vgrd.addColorStop(0, 'rgba(0,10,30,0)');
    vgrd.addColorStop(1, 'rgba(0,0,10,0.55)');
    bctx.fillStyle = vgrd;
    bctx.fillRect(0, 0, W, H);

    drawHexNodes();
    drawArcReactor();
    drawOrbits();
    drawParticlesLinked();
    drawShards();
    drawDNA();
    drawScanLine();
    drawMiniCharts();

    if (frameIndex % 30 === 0) updateUptime();
  }

  window.addEventListener('resize', () => {
    W = wrap.clientWidth;
    H = wrap.clientHeight;
    bg.width = fg.width = W;
    bg.height = fg.height = H;
    cx = W / 2;
    cy = H / 2 - 30;
    rebuildEntities();
  });

  animId = requestAnimationFrame(frame);

  return {
    setState: (s: OrbState) => {
      state = s;
    },
    setAnalyser: (a: AnalyserNode) => {
      analyser = a;
    },
    setReactor: (props: Partial<ReactorProps>) => {
      Object.assign(reactor, props);
    },
    getReactor: () => ({ ...reactor }),
    addOrbit: (def: OrbitDef) => {
      const img = new Image();
      const active: ActiveOrbit = {
        def,
        img,
        loaded: false,
        angle: ((def.phase ?? 0) * Math.PI) / 180,
      };
      img.onload = () => {
        active.loaded = true;
      };
      img.onerror = () => {
        console.warn('[Orbit] Failed to load image:', def.src);
      };
      img.src = resolveOrbitSrc(def.src);
      activeOrbits.set(def.id, active);
    },
    removeOrbit: (id: string) => {
      activeOrbits.delete(id);
    },
    clearOrbits: () => {
      activeOrbits.clear();
    },
    destroy: () => {
      running = false;
      if (animId) cancelAnimationFrame(animId);
    },
  };
}
