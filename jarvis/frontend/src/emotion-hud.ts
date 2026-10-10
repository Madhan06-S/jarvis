/**
 * JARVIS EMOTIONAL AI HUD
 * Renders real-time emotional state, adapts UI colors, shows mood graph.
 */

export interface EmotionState {
  emotion: string;
  color: string;
  accent: string;
  energy: number;
  wpm: number;
  confidence: number;
  history: string[];
}

const EMOTION_ICONS: Record<string, string> = {
  focused:  '🎯',
  calm:     '🌊',
  stressed: '⚡',
  excited:  '🔥',
  tired:    '🌙',
  angry:    '💢',
  anxious:  '🌀',
  neutral:  '◎',
};

const EMOTION_LABELS: Record<string, string> = {
  focused:  'FOCUSED',
  calm:     'CALM',
  stressed: 'STRESSED',
  excited:  'EXCITED',
  tired:    'TIRED',
  angry:    'ELEVATED',
  anxious:  'ANXIOUS',
  neutral:  'NOMINAL',
};

export class EmotionHUD {
  private container: HTMLElement;
  private state: EmotionState | null = null;
  private historyCanvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private historyData: number[] = [];
  private animFrame: number | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.build();
    this.historyCanvas = this.container.querySelector('#emotion-graph') as HTMLCanvasElement;
    this.ctx = this.historyCanvas.getContext('2d')!;
    this.startAnimation();
  }

  update(state: EmotionState) {
    this.state = state;
    this.historyData.push(state.energy);
    if (this.historyData.length > 60) this.historyData.shift();
    this.render();
    this.applyGlobalTheme(state);
  }

  private build() {
    this.container.innerHTML = `
      <div class="emotion-panel">
        <div class="emotion-header">
          <span class="emotion-label-title">EMOTIONAL AI</span>
          <span class="emotion-live-dot">●</span>
        </div>
        <div class="emotion-main">
          <div class="emotion-icon" id="emotion-icon">◎</div>
          <div class="emotion-info">
            <div class="emotion-name" id="emotion-name">NOMINAL</div>
            <div class="emotion-conf" id="emotion-conf">CONFIDENCE: —</div>
          </div>
        </div>
        <div class="emotion-bars">
          <div class="ebar-row">
            <span>ENERGY</span>
            <div class="ebar-track"><div class="ebar-fill" id="ebar-energy"></div></div>
            <span id="ebar-energy-val">—</span>
          </div>
          <div class="ebar-row">
            <span>WPM</span>
            <div class="ebar-track"><div class="ebar-fill" id="ebar-wpm" style="background:#ffcc00"></div></div>
            <span id="ebar-wpm-val">—</span>
          </div>
        </div>
        <canvas id="emotion-graph" width="200" height="40" style="width:100%;margin-top:8px;opacity:0.8;"></canvas>
        <div class="emotion-history" id="emotion-history"></div>
      </div>
    `;
  }

  private render() {
    if (!this.state) return;
    const s = this.state;

    const iconEl  = this.container.querySelector('#emotion-icon') as HTMLElement;
    const nameEl  = this.container.querySelector('#emotion-name') as HTMLElement;
    const confEl  = this.container.querySelector('#emotion-conf') as HTMLElement;
    const energyBar = this.container.querySelector('#ebar-energy') as HTMLElement;
    const energyVal = this.container.querySelector('#ebar-energy-val') as HTMLElement;
    const wpmBar  = this.container.querySelector('#ebar-wpm') as HTMLElement;
    const wpmVal  = this.container.querySelector('#ebar-wpm-val') as HTMLElement;
    const histEl  = this.container.querySelector('#emotion-history') as HTMLElement;

    if (iconEl)  iconEl.textContent  = EMOTION_ICONS[s.emotion] || '◎';
    if (nameEl)  { nameEl.textContent = EMOTION_LABELS[s.emotion] || s.emotion.toUpperCase(); nameEl.style.color = s.color; }
    if (confEl)  confEl.textContent  = `CONFIDENCE: ${Math.round(s.confidence * 100)}%`;
    if (energyBar) { energyBar.style.width = `${Math.min(100, s.energy * 60)}%`; energyBar.style.background = s.color; }
    if (energyVal) energyVal.textContent = s.energy.toFixed(1);
    if (wpmBar)  wpmBar.style.width = `${Math.min(100, s.wpm / 1.5)}%`;
    if (wpmVal)  wpmVal.textContent = `${Math.round(s.wpm)}`;

    if (histEl && s.history) {
      histEl.innerHTML = s.history.slice(-5).map(e =>
        `<span class="emotion-tag" style="color:${EMOTION_ICONS[e] ? s.color : '#888'}">${EMOTION_ICONS[e] || '◎'}</span>`
      ).join('');
    }

    this.drawGraph(s.color);
  }

  private drawGraph(color: string) {
    if (!this.ctx || this.historyData.length < 2) return;
    const { width, height } = this.historyCanvas;
    this.ctx.clearRect(0, 0, width, height);

    const step = width / (this.historyData.length - 1);
    const maxVal = 2.0;

    this.ctx.beginPath();
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = 1.5;
    this.ctx.shadowBlur = 6;
    this.ctx.shadowColor = color;

    this.historyData.forEach((v, i) => {
      const x = i * step;
      const y = height - (v / maxVal) * height * 0.85 - 2;
      if (i === 0) this.ctx.moveTo(x, y);
      else this.ctx.lineTo(x, y);
    });
    this.ctx.stroke();
    this.ctx.shadowBlur = 0;
  }

  private applyGlobalTheme(state: EmotionState) {
    // Smoothly update CSS variables for global color adaptation
    document.documentElement.style.setProperty('--emotion-color', state.color);
    document.documentElement.style.setProperty('--emotion-accent', state.accent);
  }

  private startAnimation() {
    const tick = () => {
      if (this.state) this.drawGraph(this.state.color);
      this.animFrame = requestAnimationFrame(tick);
    };
    this.animFrame = requestAnimationFrame(tick);
  }

  destroy() {
    if (this.animFrame) cancelAnimationFrame(this.animFrame);
  }
}
