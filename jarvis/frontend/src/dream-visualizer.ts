/**
 * JARVIS DREAM MODE VISUALIZER
 * Renders floating thought bubbles, neural dreaming sequences,
 * holographic imagination system when JARVIS is idle.
 */

interface DreamThought {
  text: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  alpha: number;
  size: number;
  color: string;
  age: number;
}

const DREAM_COLORS = ['#00BFFF', '#cc44ff', '#ffcc00', '#00ff88', '#ff8800'];

export class DreamVisualizer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private thoughts: DreamThought[] = [];
  private isActive = false;
  private animFrame: number | null = null;
  private particles: Array<{x:number;y:number;vx:number;vy:number;r:number;alpha:number;color:string}> = [];
  private dreamCount = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  activate(thought?: string) {
    this.isActive = true;
    this.dreamCount++;
    if (thought) this.addThought(thought);
    this.spawnParticles();
    if (!this.animFrame) this.loop();
  }

  deactivate() {
    this.isActive = false;
    // Fade out gracefully — don't stop loop immediately
    setTimeout(() => {
      if (!this.isActive) {
        if (this.animFrame) cancelAnimationFrame(this.animFrame);
        this.animFrame = null;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
    }, 3000);
  }

  addThought(text: string) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const color = DREAM_COLORS[Math.floor(Math.random() * DREAM_COLORS.length)];

    this.thoughts.push({
      text:  text.slice(0, 80),
      x:     w * 0.2 + Math.random() * w * 0.6,
      y:     h * 0.3 + Math.random() * h * 0.4,
      vx:    (Math.random() - 0.5) * 0.3,
      vy:    -(0.2 + Math.random() * 0.4),
      alpha: 0,
      size:  11 + Math.random() * 4,
      color,
      age:   0,
    });

    if (this.thoughts.length > 8) this.thoughts.shift();
  }

  private spawnParticles() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    for (let i = 0; i < 40; i++) {
      const color = DREAM_COLORS[Math.floor(Math.random() * DREAM_COLORS.length)];
      this.particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.6,
        vy: -(0.3 + Math.random() * 0.8),
        r: 1 + Math.random() * 2.5,
        alpha: 0.3 + Math.random() * 0.5,
        color,
      });
    }
  }

  private loop() {
    this.animFrame = requestAnimationFrame(() => this.loop());
    const { width: w, height: h } = this.canvas;

    this.ctx.clearRect(0, 0, w, h);

    if (!this.isActive && this.thoughts.length === 0 && this.particles.length === 0) return;

    // Draw dream overlay
    if (this.isActive) {
      const grad = this.ctx.createRadialGradient(w/2, h/2, 0, w/2, h/2, Math.max(w,h)*0.6);
      grad.addColorStop(0, 'rgba(80,0,120,0.04)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      this.ctx.fillStyle = grad;
      this.ctx.fillRect(0, 0, w, h);
    }

    // Update & draw particles
    this.particles = this.particles.filter(p => p.alpha > 0.01);
    for (const p of this.particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.alpha *= 0.995;
      if (p.y < 0) p.y = h;
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;

      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color + Math.round(p.alpha * 255).toString(16).padStart(2,'0');
      this.ctx.shadowBlur = 8;
      this.ctx.shadowColor = p.color;
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    }

    // Update & draw thought bubbles
    this.thoughts = this.thoughts.filter(t => t.alpha > 0.01 || t.age < 20);
    for (const t of this.thoughts) {
      t.age++;
      t.x += t.vx;
      t.y += t.vy;

      // Fade in then out
      if (t.age < 30) t.alpha = Math.min(0.9, t.alpha + 0.04);
      else if (t.age > 180) t.alpha = Math.max(0, t.alpha - 0.015);

      if (t.alpha <= 0) continue;

      this.ctx.save();
      this.ctx.globalAlpha = t.alpha;
      this.ctx.font = `${t.size}px 'Orbitron', monospace`;
      this.ctx.fillStyle = t.color;
      this.ctx.shadowBlur = 12;
      this.ctx.shadowColor = t.color;

      // Wrap text
      const maxW = 300;
      const words = t.text.split(' ');
      let line = '';
      let lineY = t.y;
      for (const word of words) {
        const test = line + word + ' ';
        if (this.ctx.measureText(test).width > maxW && line) {
          this.ctx.fillText(line, t.x, lineY);
          line = word + ' ';
          lineY += t.size * 1.4;
        } else {
          line = test;
        }
      }
      if (line) this.ctx.fillText(line, t.x, lineY);

      this.ctx.restore();
    }

    // Dream mode label
    if (this.isActive) {
      this.ctx.save();
      this.ctx.font = "10px 'Orbitron', monospace";
      this.ctx.fillStyle = 'rgba(180,100,255,0.5)';
      this.ctx.letterSpacing = '3px';
      this.ctx.fillText('◈ DREAM MODE ACTIVE', 20, h - 20);
      this.ctx.restore();
    }
  }

  private resize() {
    this.canvas.width  = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }
}
