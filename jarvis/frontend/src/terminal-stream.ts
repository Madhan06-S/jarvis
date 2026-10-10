/**
 * Virtualized, batched terminal log stream — caps DOM growth and batches updates.
 */

export interface TerminalLine {
  prefix: string;
  message: string;
  color: string;
  ts: number;
}

const MAX_LINES = 180;
const VISIBLE_BUFFER = 120;
const FLUSH_MS = 48;

export class TerminalStream {
  private container: HTMLElement;
  private lines: TerminalLine[] = [];
  private pending: TerminalLine[] = [];
  private flushTimer: ReturnType<typeof setTimeout> | null = null;
  private onAppend?: () => void;
  private soundThrottle = 0;

  constructor(container: HTMLElement, onAppend?: () => void) {
    this.container = container;
    this.onAppend = onAppend;
  }

  push(prefix: string, message: string, color = '#33ff66') {
    this.pending.push({ prefix, message, color, ts: Date.now() });
    if (!this.flushTimer) {
      this.flushTimer = setTimeout(() => this.flush(), FLUSH_MS);
    }
  }

  clear() {
    this.lines = [];
    this.pending = [];
    this.container.innerHTML = '';
  }

  private flush() {
    this.flushTimer = null;
    if (this.pending.length === 0) return;

    this.lines.push(...this.pending);
    this.pending = [];

    if (this.lines.length > MAX_LINES) {
      this.lines = this.lines.slice(-MAX_LINES);
    }

    this.render();
    this.container.scrollTop = this.container.scrollHeight;

    const now = performance.now();
    if (this.onAppend && now - this.soundThrottle > 120) {
      this.soundThrottle = now;
      this.onAppend();
    }
  }

  private render() {
    const slice = this.lines.slice(-VISIBLE_BUFFER);
    const frag = document.createDocumentFragment();

    for (const line of slice) {
      const divEl = document.createElement('div');
      divEl.style.marginBottom = '6px';

      if (line.prefix) {
        const spanPrefix = document.createElement('span');
        spanPrefix.textContent = `[ ${line.prefix} ] `;
        spanPrefix.style.color = line.color === '#33ff66' ? '#00e5ff' : line.color;
        spanPrefix.style.fontWeight = 'bold';
        divEl.appendChild(spanPrefix);
      }

      const spanMsg = document.createElement('span');
      spanMsg.textContent = line.message;
      spanMsg.style.color = line.color;
      divEl.appendChild(spanMsg);
      frag.appendChild(divEl);
    }

    this.container.replaceChildren(frag);
  }
}
