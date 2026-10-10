/**
 * JARVIS EVOLVED HUD PANELS
 * Cyber Defense, Power Management, Memory Timeline, Face Security panels.
 */

// ── Cyber Defense Panel ───────────────────────────────────────────────────────
export function renderCyberPanel(container: HTMLElement, data: any) {
  const level = data?.threat_level ?? 0;
  const color = level === 0 ? '#00ff88' : level < 4 ? '#ffcc00' : '#ff3300';
  const label = level === 0 ? 'SECURE' : level < 4 ? 'CAUTION' : 'THREAT';

  container.innerHTML = `
    <div class="hud-panel-title">CYBER DEFENSE <span style="color:${color}" class="blink-fast">●</span></div>
    <div class="cyber-threat-bar">
      <div class="cyber-bar-fill" style="width:${level*10}%;background:${color};box-shadow:0 0 8px ${color}"></div>
    </div>
    <div class="cyber-row"><span>STATUS</span><span style="color:${color}">${label}</span></div>
    <div class="cyber-row"><span>THREAT LVL</span><span style="color:${color}">${level}/10</span></div>
    <div class="cyber-row"><span>CONNECTIONS</span><span>${data?.connection_count ?? 0}</span></div>
    <div class="cyber-row"><span>SCANS</span><span>${data?.scan_count ?? 0}</span></div>
    ${(data?.active_threats ?? []).slice(0,2).map((t: any) =>
      `<div class="cyber-alert" style="color:#ff6600;font-size:9px;margin-top:4px">⚠ ${(t.detail||'').slice(0,40)}</div>`
    ).join('')}
    <div class="cyber-radar">
      <canvas id="cyber-radar-canvas" width="80" height="80"></canvas>
    </div>
  `;
  drawRadar(container.querySelector('#cyber-radar-canvas') as HTMLCanvasElement, level, color);
}

function drawRadar(canvas: HTMLCanvasElement | null, level: number, color: string) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d')!;
  const cx = 40, cy = 40, r = 35;
  ctx.clearRect(0, 0, 80, 80);

  // Rings
  for (let i = 1; i <= 3; i++) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * i / 3, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(0,191,255,${0.15 * i})`;
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }

  // Sweep line
  const angle = (Date.now() / 1000) % (Math.PI * 2);
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.shadowBlur = 6;
  ctx.shadowColor = color;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Threat blips
  if (level > 0) {
    for (let i = 0; i < Math.min(level, 5); i++) {
      const a = (i / 5) * Math.PI * 2 + Date.now() / 3000;
      const d = 10 + (i * 7) % 25;
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * d, cy + Math.sin(a) * d, 2, 0, Math.PI * 2);
      ctx.fillStyle = '#ff3300';
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#ff3300';
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }
}

// ── Power Management Panel ────────────────────────────────────────────────────
export function renderPowerPanel(container: HTMLElement, data: any) {
  const mode = data?.power_mode ?? 'balanced';
  const modeColors: Record<string, string> = {
    eco: '#00ff88', balanced: '#00BFFF', performance: '#ffcc00', turbo: '#ff6600'
  };
  const color = modeColors[mode] ?? '#00BFFF';
  const bat = data?.battery;
  const batColor = bat == null ? '#888' : bat < 20 ? '#ff3300' : bat < 50 ? '#ffcc00' : '#00ff88';

  container.innerHTML = `
    <div class="hud-panel-title">POWER MANAGEMENT</div>
    <div class="power-mode-badge" style="color:${color};border-color:${color}40">${mode.toUpperCase()} MODE</div>
    <div class="power-row"><span>CPU</span>
      <div class="power-bar-track"><div class="power-bar-fill" style="width:${data?.cpu??0}%;background:${data?.cpu>80?'#ff3300':'#00BFFF'}"></div></div>
      <span>${data?.cpu??0}%</span>
    </div>
    <div class="power-row"><span>RAM</span>
      <div class="power-bar-track"><div class="power-bar-fill" style="width:${data?.ram??0}%;background:#cc44ff"></div></div>
      <span>${data?.ram??0}%</span>
    </div>
    <div class="power-row"><span>TEMP</span><span style="color:${(data?.temp??0)>80?'#ff3300':'#00ff88'}">${data?.temp??'—'}°C</span></div>
    ${bat != null ? `
    <div class="power-row"><span>BATTERY</span>
      <div class="power-bar-track"><div class="power-bar-fill" style="width:${bat}%;background:${batColor}"></div></div>
      <span style="color:${batColor}">${bat}% ${data?.charging?'⚡':''}</span>
    </div>` : ''}
    <div class="power-actions">
      ${['eco','balanced','performance'].map(m =>
        `<button class="power-mode-btn ${m===mode?'active':''}" onclick="window._setPowerMode('${m}')" style="${m===mode?`border-color:${color};color:${color}`:''}">
          ${m.toUpperCase()}
        </button>`
      ).join('')}
    </div>
    ${(data?.recent_actions??[]).slice(-2).map((a:any)=>
      `<div style="font-size:9px;color:#ffcc00;margin-top:3px">⚡ ${a.action}</div>`
    ).join('')}
  `;
}

// ── Face Security Panel ───────────────────────────────────────────────────────
export function renderFacePanel(container: HTMLElement, data: any) {
  const authorized = data?.authorized;
  const stranger   = data?.stranger_alert;
  const running    = data?.running;
  const color = stranger ? '#ff3300' : authorized ? '#00ff88' : '#ffcc00';
  const status = stranger ? 'INTRUDER DETECTED' : authorized ? 'AUTHORIZED' : running ? 'SCANNING' : 'OFFLINE';

  container.innerHTML = `
    <div class="hud-panel-title">BIOMETRIC SECURITY <span style="color:${color}" class="blink-fast">●</span></div>
    <div class="face-status" style="color:${color}">${status}</div>
    <div class="face-scan-ring" style="border-color:${color}40;box-shadow:0 0 12px ${color}30">
      <div class="face-scan-inner" style="border-color:${color}">
        <span style="font-size:24px">${stranger?'👤':'🔒'}</span>
      </div>
      <div class="face-scan-line" style="background:${color}"></div>
    </div>
    <div class="face-row"><span>FACES</span><span>${data?.face_count??0}</span></div>
    <div class="face-row"><span>ATTENTION</span>
      <div class="power-bar-track"><div class="power-bar-fill" style="width:${(data?.attention??0)*100}%;background:${color}"></div></div>
    </div>
    <div class="face-row"><span>KNOWN USERS</span><span>${(data?.known_users??[]).length}</span></div>
    ${!running ? `
    <button class="face-start-btn" onclick="window._startFaceSecurity()">ACTIVATE BIOMETRICS</button>
    ` : ''}
    ${stranger ? `<div class="face-alert">⚠ UNKNOWN INDIVIDUAL DETECTED — STEALTH MODE ACTIVE</div>` : ''}
  `;
}

// ── Memory Timeline Panel ─────────────────────────────────────────────────────
export function renderMemoryPanel(container: HTMLElement, data: any[]) {
  if (!data || data.length === 0) {
    container.innerHTML = `<div class="hud-panel-title">MEMORY TIMELINE</div><div style="color:#444;font-size:10px;padding:8px">No memories yet.</div>`;
    return;
  }

  const typeColors: Record<string, string> = {
    fact: '#00BFFF', preference: '#00ff88', project: '#ffcc00',
    person: '#ff8800', decision: '#cc44ff', goal: '#ff4444', conversation: '#aaaaff',
  };

  container.innerHTML = `
    <div class="hud-panel-title">MEMORY TIMELINE <span style="font-size:9px;color:#444">${data.length} nodes</span></div>
    <div class="memory-timeline-list">
      ${data.slice(0, 8).map(m => {
        const color = typeColors[m.type] ?? '#00BFFF';
        const age   = m.visual?.age_label ?? m.age_label ?? '';
        return `
          <div class="memory-node" style="border-left-color:${color}">
            <div class="memory-node-type" style="color:${color}">${(m.type||'fact').toUpperCase()}</div>
            <div class="memory-node-content">${(m.content||'').slice(0,55)}${m.content?.length>55?'…':''}</div>
            <div class="memory-node-age">${age}</div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ── Dream Mode Panel ──────────────────────────────────────────────────────────
export function renderDreamPanel(container: HTMLElement, data: any) {
  const dreaming = data?.dreaming;
  const thought  = data?.last_dream ?? '';
  const count    = data?.dream_count ?? 0;
  const idle     = data?.idle_secs ?? 0;

  container.innerHTML = `
    <div class="hud-panel-title">
      DREAM MODE
      ${dreaming ? '<span style="color:#cc44ff" class="blink-fast">◈ ACTIVE</span>' : '<span style="color:#444">STANDBY</span>'}
    </div>
    ${dreaming ? `
      <div class="dream-thought-box">
        <div class="dream-thought-text">${thought.slice(0, 120)}${thought.length > 120 ? '…' : ''}</div>
      </div>
    ` : `
      <div style="font-size:9px;color:#444;padding:4px 0">
        IDLE: ${Math.round(idle)}s / 120s until dream
      </div>
      <div class="dream-idle-bar">
        <div class="dream-idle-fill" style="width:${Math.min(100, idle/1.2)}%"></div>
      </div>
    `}
    <div style="font-size:9px;color:#666;margin-top:6px">DREAMS: ${count}</div>
  `;
}
