import { createSocket } from './ws';
import { VoiceInput, AudioPlayer } from './voice';
import { createOrb, OrbState } from './orb';
import { getPerformanceManager } from './performance-manager';
import { TerminalStream } from './terminal-stream';
import { PreviewManager } from './preview-manager';
import { EmotionHUD } from './emotion-hud';
import { DreamVisualizer } from './dream-visualizer';
import {
  renderCyberPanel, renderPowerPanel,
  renderFacePanel, renderMemoryPanel, renderDreamPanel
} from './hud-panels';

const statusEl = document.getElementById('status-text')!;
const errEl    = document.getElementById('error-text')!;

// ── SciFi Sound Engine ────────────────────────────────────────────────────────
class SciFiSoundEngine {
  private ctx: AudioContext | null = null;
  public isMuted = false;
  private init() {
    if (!this.ctx && !this.isMuted) {
      try { this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)(); } catch {}
    }
  }
  playTyping() {
    this.init(); if (!this.ctx || this.isMuted) return;
    const now = this.ctx.currentTime;
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = 'triangle'; o.frequency.setValueAtTime(700 + Math.random()*500, now);
    g.gain.setValueAtTime(0.015, now); g.gain.exponentialRampToValueAtTime(0.0001, now+0.05);
    o.connect(g); g.connect(this.ctx.destination); o.start(now); o.stop(now+0.05);
  }
  playSweep() {
    this.init(); if (!this.ctx || this.isMuted) return;
    const now = this.ctx.currentTime;
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(250, now);
    o.frequency.exponentialRampToValueAtTime(1400, now+0.4);
    g.gain.setValueAtTime(0.05, now); g.gain.exponentialRampToValueAtTime(0.0001, now+0.4);
    o.connect(g); g.connect(this.ctx.destination); o.start(now); o.stop(now+0.4);
  }
  playWarning() {
    this.init(); if (!this.ctx || this.isMuted) return;
    const now = this.ctx.currentTime;
    const o1 = this.ctx.createOscillator(), o2 = this.ctx.createOscillator(), g = this.ctx.createGain();
    o1.frequency.setValueAtTime(190, now); o2.frequency.setValueAtTime(194, now);
    g.gain.setValueAtTime(0.08, now); g.gain.exponentialRampToValueAtTime(0.0001, now+0.45);
    o1.connect(g); o2.connect(g); g.connect(this.ctx.destination);
    o1.start(now); o2.start(now); o1.stop(now+0.45); o2.stop(now+0.45);
  }
  playSuccess() {
    this.init(); if (!this.ctx || this.isMuted) return;
    const now = this.ctx.currentTime;
    [523.25, 659.25, 783.99, 1046.50].forEach((freq, i) => {
      const o = this.ctx!.createOscillator(), g = this.ctx!.createGain();
      o.frequency.setValueAtTime(freq, now+i*0.08);
      g.gain.setValueAtTime(0.03, now+i*0.08);
      g.gain.exponentialRampToValueAtTime(0.0001, now+i*0.08+0.35);
      o.connect(g); g.connect(this.ctx!.destination);
      o.start(now+i*0.08); o.stop(now+i*0.08+0.35);
    });
  }
}
const synth = new SciFiSoundEngine();

// ── Architecture Canvas ───────────────────────────────────────────────────────
class ArchitectureCanvas {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animId: number | null = null;
  private visible = false;
  public progressPct = 0;
  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d')!;
  }
  start() {
    if (this.animId) return; this.visible = true;
    const render = () => { if (!this.visible) return; this.draw(); this.animId = requestAnimationFrame(render); };
    render();
  }
  stop() { this.visible = false; if (this.animId) { cancelAnimationFrame(this.animId); this.animId = null; } }
  private draw() {
    const { width: w, height: h } = this.canvas;
    this.ctx.clearRect(0, 0, w, h);
    const nodes = [
      { name:'FRONTEND', x:50,  y:95,  color:'#00e5ff', glow: this.progressPct>20 },
      { name:'API',      x:150, y:45,  color:'#ff8c00', glow: this.progressPct>50 },
      { name:'BACKEND',  x:150, y:145, color:'#ff8c00', glow: this.progressPct>60 },
      { name:'DATABASE', x:250, y:95,  color:'#00ff88', glow: this.progressPct>80 },
    ];
    const conns = [{from:0,to:1},{from:0,to:2},{from:1,to:3},{from:2,to:3}];
    this.ctx.lineWidth = 2;
    conns.forEach(c => {
      const n1=nodes[c.from], n2=nodes[c.to];
      this.ctx.beginPath(); this.ctx.moveTo(n1.x,n1.y); this.ctx.lineTo(n2.x,n2.y);
      const active = n1.glow && n2.glow;
      this.ctx.strokeStyle = active ? 'rgba(0,229,255,0.75)' : 'rgba(0,229,255,0.15)';
      this.ctx.shadowBlur = active ? 10 : 0; this.ctx.shadowColor = '#00e5ff';
      this.ctx.stroke();
      if (active) {
        const t = (performance.now()*0.002)%1;
        const px=n1.x+(n2.x-n1.x)*t, py=n1.y+(n2.y-n1.y)*t;
        this.ctx.beginPath(); this.ctx.arc(px,py,4,0,Math.PI*2);
        this.ctx.fillStyle='#fff'; this.ctx.shadowBlur=12; this.ctx.fill();
      }
    });
    this.ctx.shadowBlur=0;
    nodes.forEach(n => {
      this.ctx.beginPath(); this.ctx.arc(n.x,n.y,22,0,Math.PI*2);
      this.ctx.fillStyle = n.glow?'rgba(0,11,24,0.9)':'rgba(0,5,10,0.55)';
      this.ctx.strokeStyle = n.glow?n.color:'rgba(0,229,255,0.2)';
      this.ctx.lineWidth = n.glow?2:1;
      this.ctx.shadowBlur = n.glow?12:0; this.ctx.shadowColor=n.color;
      this.ctx.fill(); this.ctx.stroke(); this.ctx.shadowBlur=0;
      this.ctx.fillStyle = n.glow?'#fff':'rgba(0,229,255,0.4)';
      this.ctx.font="bold 8px 'Share Tech Mono',monospace";
      this.ctx.textAlign='center'; this.ctx.fillText(n.name,n.x,n.y+3);
    });
  }
}

function main() {
  const perf    = getPerformanceManager();
  const orb     = createOrb(document.getElementById('orb-canvas') as HTMLCanvasElement);
  const preview = new PreviewManager();
  const audio   = new AudioPlayer();
  orb.setAnalyser(audio.getAnalyser());
  audio.ensureUnlocked();

  // Dream visualizer
  const dreamCanvas = document.getElementById('dream-canvas') as HTMLCanvasElement;
  const dreamViz = dreamCanvas ? new DreamVisualizer(dreamCanvas) : null;

  // Emotion HUD
  const emotionContainer = document.getElementById('emotion-hud-container');
  const emotionHUD = emotionContainer ? new EmotionHUD(emotionContainer) : null;

  // Evolved panel containers
  const cyberContainer  = document.getElementById('cyber-panel-container');
  const powerContainer  = document.getElementById('power-panel-container');
  const faceContainer   = document.getElementById('face-panel-container');
  const memoryContainer = document.getElementById('memory-panel-container');
  const dreamContainer  = document.getElementById('dream-panel-container');

  let state: OrbState = 'idle';
  let isMuted = false;
  synth.isMuted = isMuted;

  const isElectron = /electron/i.test(navigator.userAgent);
  if (isElectron) {
    setTimeout(() => {
      appendHudLog('SYSTEM', 'ELECTRON DETECTED: Utilizing backend neural speech processor.', '#00ff88');
    }, 1500);
  }

  let currentYtPlayer: any = null;
  let voiceWatchdogTimer: any = null;
  let voiceStage = 'idle';

  function resetVoiceWatchdog() {
    if (voiceWatchdogTimer) {
      clearTimeout(voiceWatchdogTimer);
      voiceWatchdogTimer = null;
    }
  }

  function startVoiceWatchdog(stage = 'transcribing') {
    resetVoiceWatchdog();
    voiceStage = stage;
    console.log(`[HUD Watchdog] Started 12s timeout guard for voice stage: '${stage}'`);
    voiceWatchdogTimer = setTimeout(() => {
      if (state === 'transcribing' || state === 'thinking' || state === 'listening') {
        let reason = 'STT TRANSCRIPTION TIMEOUT (NO RESPONSE FROM BACKEND)';
        if (voiceStage === 'listening') {
          reason = 'NO SPEECH DETECTED (RMS TOO LOW / SILENCE)';
        } else if (!socket.isConnected()) {
          reason = 'VOICE WEBSOCKET DISCONNECTED (CHECK AUTHENTICATION)';
        }
        console.warn(`[HUD Watchdog] 12s timeout reached! Diagnostic failure: ${reason}`);
        appendHudLog('SPEECH_TIMEOUT', reason, '#ff9900');
        errEl.innerText = reason;
        errEl.style.opacity = '1';
        setTimeout(() => { errEl.style.opacity = '0'; }, 5000);
        setState('idle');
      }
    }, 12000);
  }

  function destroyCurrentMusicPlayer() {
    console.log('[HUD Media Player] Destroying previous music player instance...');
    if (currentYtPlayer) {
      try {
        if (typeof currentYtPlayer.destroy === 'function') currentYtPlayer.destroy();
        else if (typeof currentYtPlayer.pauseVideo === 'function') currentYtPlayer.pauseVideo();
      } catch (e) {
        console.warn('[HUD Media Player] Error cleaning previous player:', e);
      }
      currentYtPlayer = null;
    }
    const oldIframe = document.getElementById('yt-player-iframe');
    if (oldIframe) {
      oldIframe.setAttribute('src', '');
      oldIframe.remove();
    }
  }

  const voice = new VoiceInput(
    (t) => {
      if (isMuted) return;
      audio.stop();
      console.log(`[Voice Pipeline] WebSpeech transcript received: "${t}". Sending to socket...`);
      socket.send({ type: 'transcript', text: t, isFinal: true });
      setState('thinking');
      startVoiceWatchdog('thinking');
    },
    (err) => {
      if (err === 'aborted' || err === 'no-speech') return;
      console.error(`[Voice Pipeline] Voice engine error: ${err}`);
      appendHudLog('SPEECH_ERROR', `Voice Engine: ${err.toUpperCase()}`, '#ff3300');
      errEl.innerText = err;
      errEl.style.opacity = '1';
      setTimeout(() => { errEl.style.opacity = '0'; }, 6000);
      resetVoiceWatchdog();
      setState('idle');
    },
    (base64Wav) => {
      if (isMuted) return;
      audio.stop();
      const isConnected = socket.isConnected();
      console.log(`[Voice Pipeline] Encoded audio_input (${base64Wav.length} b64 chars). WS Connected: ${isConnected}`);
      if (!isConnected) {
        errEl.innerText = "VOICE WEBSOCKET DISCONNECTED. PLEASE CHECK AUTH TOKEN.";
        errEl.style.opacity = '1';
        setTimeout(() => { errEl.style.opacity = '0'; }, 5000);
        setState('idle');
        return;
      }
      socket.send({ type: 'audio_input', data: base64Wav });
      setState('transcribing');
      startVoiceWatchdog('audio_sent');
    },
    (st) => {
      if (isMuted) return;
      setState(st);
      if (st === 'transcribing' || st === 'thinking') startVoiceWatchdog(st);
    }
  );

  const micContainer = document.getElementById('mic-level-container');
  const micFill = document.getElementById('mic-level-fill');
  const micDeviceLabel = document.getElementById('mic-device-label');

  voice.onDeviceChange = (deviceName) => {
    if (micDeviceLabel) {
      micDeviceLabel.innerText = `MIC: ${deviceName.toUpperCase()}`;
      micDeviceLabel.style.display = 'block';
    }
  };

  voice.onMicLevel = (pct) => {
    if (micContainer && micFill) {
      micContainer.style.display = pct > 0 ? 'block' : 'none';
      micFill.style.width = `${pct}%`;
    }
  };

  voice.onWake = () => {
    if (isMuted) return;
    audio.stop(); synth.playSweep(); setState('listening');
    appendHudLog('WAKE_AI', 'Wake word detected. Audio stream open.', '#00ff88');
  };

  const btnMute = document.getElementById('btn-mute')!;
  btnMute.addEventListener('click', () => {
    isMuted = !isMuted; synth.isMuted = isMuted;
    if (isMuted) { btnMute.classList.add('muted'); voice.pause(); }
    else { btnMute.classList.remove('muted'); if (state==='idle'||state==='listening') voice.start(); }
  });

  const sysStatusBadge = document.getElementById('system-status-badge');
  const chatInputEl = document.getElementById('chat-input') as HTMLInputElement;

  function setState(s: OrbState) {
    state = s; orb.setState(s);
    if (sysStatusBadge) {
      sysStatusBadge.style.display = 'block';
      sysStatusBadge.innerText = `[ ${s.toUpperCase()} ]`;
      if (s === 'thinking') sysStatusBadge.style.borderColor = 'rgba(255, 200, 0, 0.8)';
      else if (s === 'transcribing') sysStatusBadge.style.borderColor = 'rgba(255, 215, 0, 0.9)';
      else if (s === 'executing') sysStatusBadge.style.borderColor = 'rgba(0, 255, 136, 0.9)';
      else if (s === 'speaking') sysStatusBadge.style.borderColor = 'rgba(0, 191, 255, 0.8)';
      else if (s === 'listening') sysStatusBadge.style.borderColor = 'rgba(0, 255, 200, 0.8)';
      else sysStatusBadge.style.borderColor = 'rgba(0, 191, 255, 0.5)';
    }

    if (statusEl) {
      if (s === 'idle') {
        statusEl.style.display = 'none';
        statusEl.innerText = '';
        if (chatInputEl) chatInputEl.placeholder = '// Speak or type a command, sir...';
        if (!isMuted) setTimeout(()=>voice.start(),800);
      } else {
        statusEl.style.display = 'block';
        statusEl.innerText = s.toUpperCase();
        if (chatInputEl) chatInputEl.placeholder = '';
        if (s === 'listening') { if (!isMuted) voice.start(); }
        else if (s === 'transcribing') { voice.pause(); }
        else if (s === 'thinking') { voice.pause(); }
        else if (s === 'executing') { voice.pause(); }
        else if (s === 'speaking') { voice.pause(); }
      }
    }

    if (s === 'idle') resetVoiceWatchdog();
    if (s !== 'idle') authFetch('/api/dream/status').catch(()=>{});
  }

  function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = localStorage.getItem('jarvis_token') || '';
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return fetch(url, { ...options, headers }).then((res) => {
      if (res.status === 401) {
        showAuthModal("Session expired or invalid access token. Please re-authenticate.");
      }
      return res;
    });
  }

  function showAuthModal(errorMsg: string = '') {
    const modal = document.getElementById('auth-modal');
    const errEl = document.getElementById('auth-error-msg');
    if (modal) modal.style.display = 'flex';
    if (errEl) {
      if (errorMsg) {
        errEl.innerText = errorMsg;
        errEl.style.display = 'block';
      } else {
        errEl.style.display = 'none';
      }
    }
  }

  function hideAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.style.display = 'none';
  }

  window.addEventListener("jarvis_auth_failed", () => {
    showAuthModal("Invalid Access Token. Connection rejected by JARVIS Security.");
  });

  const storedToken = localStorage.getItem('jarvis_token');
  if (!storedToken) {
    showAuthModal();
  }

  const authSubmitBtn = document.getElementById('auth-submit-btn');
  const authTokenInput = document.getElementById('auth-token-input') as HTMLInputElement;
  if (authSubmitBtn && authTokenInput) {
    authSubmitBtn.addEventListener('click', () => {
      const val = authTokenInput.value ? authTokenInput.value.trim() : '';
      if (val) {
        localStorage.setItem('jarvis_token', val);
        hideAuthModal();
        location.reload();
      }
    });
  }

  document.getElementById('btn-logout-auth')?.addEventListener('click', () => {
    localStorage.removeItem('jarvis_token');
    showAuthModal("Session locked.");
  });

  const wsHost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? '127.0.0.1' : location.hostname;
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsPort = location.port === '5173' || location.port === '' ? (location.port === '' ? '' : ':8340') : `:${location.port}`;
  console.log(`⚡ [JARVIS HUD] v3.0.4-LIVE-MIC loaded fresh at ${new Date().toISOString()}`);

  const wsUrl = `${wsProtocol}//${wsHost}${wsPort || ':8340'}/ws/voice`;
  const socket = createSocket(wsUrl);

  socket.onConnectionChange(conn => {
    if (conn) {
      errEl.style.opacity='0';
      setTimeout(()=>setState('listening'),1000);
    }
    else { errEl.innerText='Reconnecting to JARVIS...'; errEl.style.opacity='1'; voice.pause(); setState('idle'); }
  });
  audio.onFinished(() => { setState('idle'); voice.resetWakeState(); });

  // ── Build HUD ──────────────────────────────────────────────────────────────
  const hudOverlay     = document.getElementById('autonomous-build-hud')!;
  const hudTermLogs    = document.getElementById('hud-terminal-logs')!;
  const hudTermInput   = document.getElementById('hud-terminal-input')!;
  const hudThought     = document.getElementById('hud-thought-text')!;
  const hudFileLogs    = document.getElementById('hud-file-logs')!;
  const hudProgFill    = document.getElementById('hud-progress-fill')!;
  const hudProgText    = document.getElementById('hud-progress-text')!;
  const hudProgPct     = document.getElementById('hud-progress-pct')!;
  const hudCloseBtn    = document.getElementById('hud-close-btn')!;
  const archCanvas     = document.getElementById('hud-architecture-canvas') as HTMLCanvasElement;
  const archViz        = new ArchitectureCanvas(archCanvas);
  const hudTerminal    = new TerminalStream(hudTermLogs, ()=>synth.playTyping());
  let progInterval: any = null;
  let simProg = 0;

  function appendHudLog(prefix: string, msg: string, color='#33ff66') {
    hudTerminal.push(prefix, msg, color);
  }

  function setAgentStatus(id: string, status: string, log: string, pct: number) {
    const card = document.getElementById(`hud-agent-${id}`); if (!card) return;
    const badge = card.querySelector('.agent-hud-status')!;
    const logEl = card.querySelector('.agent-hud-log')!;
    const bar   = card.querySelector('.agent-hud-bar') as HTMLElement;
    card.className = `agent-hud-card ${status}-state`;
    badge.className = `agent-hud-status ${status}`;
    badge.textContent = status.toUpperCase();
    logEl.textContent = log;
    if (bar) bar.style.width = `${pct}%`;
    if (status==='error') synth.playWarning();
  }

  function typeCmd(cmd: string, cb: ()=>void) {
    let i=0; hudTermInput.textContent='';
    const t = setInterval(()=>{
      if (i<cmd.length) { hudTermInput.textContent+=cmd[i++]; synth.playTyping(); }
      else { clearInterval(t); setTimeout(()=>{ appendHudLog('sir@jarvis-os',`$ ${cmd}`,'#00e5ff'); hudTermInput.textContent=''; cb(); },400); }
    },35);
  }

  function addFileOp(op: string, path: string, st: string) {
    const item = document.createElement('div'); item.className='file-log-item';
    item.innerHTML=`<span class="file-log-op ${op.toLowerCase()}">[${op}]</span><span class="file-log-path">${path}</span><span class="file-log-status ${st.toLowerCase()}">${st}</span>`;
    hudFileLogs.appendChild(item);
    while(hudFileLogs.children.length>80) hudFileLogs.removeChild(hudFileLogs.firstChild!);
    hudFileLogs.scrollTop=hudFileLogs.scrollHeight;
  }

  function setPhase(phase: string) {
    ['planning','generation','debugging','deployment'].forEach((s,i)=>{
      const el=document.getElementById(`hud-stage-${s}`)!;
      const idx=['planning','generation','debugging','deployment'].indexOf(phase);
      el.className=`hud-stage${i===idx?' active':i<idx?' completed':''}`;
    });
  }

  function triggerBuildHUD() {
    setState('thinking'); hudOverlay.style.display='flex'; hudCloseBtn.style.display='none';
    hudTerminal.clear(); hudFileLogs.innerHTML='';
    hudThought.textContent='Cognitive Swarm Initializing...';
    simProg=0; archViz.progressPct=0; archViz.start(); synth.playSweep();
    const acts = [
      {t:1000,type:'log',p:'SYSTEM',m:'Initializing Stark Neural Swarm...',c:'#00e5ff'},
      {t:2000,type:'agent',id:'architect',s:'thinking',m:'Parsing requirements...',p:30},
      {t:4000,type:'cmd',text:'npx @stark/check-ports --port 8000'},
      {t:6000,type:'agent',id:'security',s:'active',m:'Sandbox cleared.',p:100},
      {t:8000,type:'agent',id:'architect',s:'success',m:'Blueprint locked.',p:100},
      {t:9000,type:'phase',phase:'generation'},
      {t:9500,type:'agent',id:'ui',s:'thinking',m:'Planning layouts...',p:25},
      {t:11000,type:'cmd',text:'npm install framer-motion gsap three'},
      {t:13000,type:'file',op:'WRITE',path:'frontend/src/App.tsx',st:'SUCCESS'},
      {t:15000,type:'agent',id:'backend',s:'thinking',m:'Resolving schemas...',p:35},
      {t:17000,type:'file',op:'WRITE',path:'backend/main.py',st:'SUCCESS'},
      {t:22000,type:'agent',id:'ui',s:'success',m:'UI assembled.',p:100},
      {t:23000,type:'agent',id:'backend',s:'success',m:'API endpoints live.',p:100},
      {t:25000,type:'phase',phase:'debugging'},
      {t:26000,type:'agent',id:'debug',s:'thinking',m:'Running type checks...',p:50},
      {t:29000,type:'agent',id:'debug',s:'success',m:'0 errors.',p:100},
      {t:33000,type:'phase',phase:'deployment'},
      {t:34000,type:'agent',id:'deployment',s:'active',m:'Bundling...',p:80},
      {t:38000,type:'file',op:'DEPLOY',path:'Vercel Edge Gateway',st:'SUCCESS'},
    ];
    acts.forEach(a=>{
      setTimeout(()=>{
        if(hudOverlay.style.display==='none') return;
        if(a.type==='log') appendHudLog(String(a.p),String(a.m),String((a as any).c||'#33ff66'));
        else if(a.type==='agent') setAgentStatus(a.id!,(a as any).s,String(a.m),Number(a.p));
        else if(a.type==='cmd') typeCmd((a as any).text,()=>{});
        else if(a.type==='file') addFileOp((a as any).op,(a as any).path,(a as any).st);
        else if(a.type==='phase') setPhase((a as any).phase);
      },a.t);
    });
    progInterval=setInterval(()=>{
      if(simProg<95){ simProg+=Math.random()*3; if(simProg>95)simProg=95;
        hudProgFill.style.width=`${simProg}%`; hudProgPct.textContent=`${Math.round(simProg)}%`;
        archViz.progressPct=simProg;
        const r=(40+Math.random()*15).toFixed(1);
        const rateEl=document.getElementById('hud-cognition-rate'); if(rateEl) rateEl.textContent=`${r} T/s`;
        hudProgText.textContent=simProg<25?'[PLANNING] MAPPING SYSTEMS...':simProg<70?'[GENERATION] COMPILING...':simProg<85?'[DEBUGGING] ANALYZING...':'[DEPLOYMENT] LAUNCHING...';
        hudThought.textContent=simProg<25?'Mapping requirements model...':simProg<70?'Generating 3D interfaces...':simProg<85?'Resolving type definitions...':'Invoking bundlers...';
      }
    },600);
  }

  function completeBuildHUD(url: string) {
    clearInterval(progInterval); simProg=100; archViz.progressPct=100;
    hudProgFill.style.width='100%'; hudProgPct.textContent='100%';
    hudProgText.textContent='SWARM PIPELINE: SUCCESSFUL!';
    ['architect','ui','motion','backend','security','debug','deployment'].forEach(id=>setAgentStatus(id,'success','Complete.',100));
    setPhase('deployment'); hudCloseBtn.style.display='block';
    hudCloseBtn.onclick=()=>{ hudOverlay.style.display='none'; archViz.stop(); setState('idle'); window.open(url,'_blank'); };
    appendHudLog('DEPLOYMENT AI','System live!','#00ff88');
    synth.playSuccess();
  }

  // ── Poll evolved system APIs ───────────────────────────────────────────────
  async function pollEvolvedSystems() {
    try {
      const [cyber, power, face, memory, dream] = await Promise.allSettled([
        authFetch('/api/cyber/status').then(r=>r.json()),
        authFetch('/api/power/status').then(r=>r.json()),
        authFetch('/api/face/status').then(r=>r.json()),
        authFetch('/api/memory/timeline?limit=8').then(r=>r.json()),
        authFetch('/api/dream/status').then(r=>r.json()),
      ]);
      if (cyberContainer  && cyber.status==='fulfilled')  renderCyberPanel(cyberContainer,   cyber.value);
      if (powerContainer  && power.status==='fulfilled')  renderPowerPanel(powerContainer,   power.value);
      if (faceContainer   && face.status==='fulfilled')   renderFacePanel(faceContainer,     face.value);
      if (memoryContainer && memory.status==='fulfilled') renderMemoryPanel(memoryContainer, memory.value);
      if (dreamContainer  && dream.status==='fulfilled')  renderDreamPanel(dreamContainer,   dream.value);
      // Dream visualizer
      if (dreamViz && dream.status==='fulfilled') {
        if (dream.value?.dreaming) dreamViz.activate();
        else dreamViz.deactivate();
      }
    } catch {}
  }
  // Disabled to prevent unnecessary GET request flooding in the terminal
  // setInterval(pollEvolvedSystems, 4000);
  // setTimeout(pollEvolvedSystems, 2000);

  // Global helpers for panel buttons
  (window as any)._setPowerMode = (mode: string) => {
    authFetch('/api/power/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})})
      .then(()=>pollEvolvedSystems());
  };
  (window as any)._startFaceSecurity = () => {
    authFetch('/api/face/start',{method:'POST'}).then(()=>{ synth.playSweep(); pollEvolvedSystems(); });
  };

  // ── WebSocket message handler ──────────────────────────────────────────────
  socket.onMessage(msg => {
    perf.recordWsMessage();
    const type = msg.type as string;

    if (type==='emotion_update') {
      if (emotionHUD) emotionHUD.update(msg as any);
      return;
    }
    if (type==='dream_start' || type==='dream_thought') {
      if (dreamViz) { dreamViz.activate((msg as any).thought); }
      if (dreamContainer) renderDreamPanel(dreamContainer, {dreaming:true, last_dream:(msg as any).thought, dream_count:(msg as any).count});
      return;
    }
    if (type==='dream_end') {
      if (dreamViz) dreamViz.deactivate();
      return;
    }
    if (type==='cyber_threat') {
      synth.playWarning();
      if (cyberContainer) authFetch('/api/cyber/status').then(r=>r.json()).then(d=>renderCyberPanel(cyberContainer!,d));
      return;
    }
    if (type==='power_event') {
      if (powerContainer) authFetch('/api/power/status').then(r=>r.json()).then(d=>renderPowerPanel(powerContainer!,d));
      return;
    }
    if (type==='face_event') {
      const ev = msg as any;
      if (ev.new_stranger) { synth.playWarning(); document.body.classList.add('stealth-mode'); setTimeout(()=>document.body.classList.remove('stealth-mode'),5000); }
      if (faceContainer) renderFacePanel(faceContainer, ev);
      return;
    }
    if (type==='gesture_event') {
      const g = msg as any;
      appendHudLog('GESTURE', `${g.gesture} → ${g.action}`, '#cc44ff');
      if (g.action==='PANEL_NEXT') switchPanel(1);
      else if (g.action==='PANEL_PREV') switchPanel(-1);
      return;
    }

    if (type==='system_stats') {
      const cpu=Math.round((msg.cpu as number)||0), ram=Math.round((msg.ram as number)||0);
      const cpuV=document.getElementById('cpu-val'), memV=document.getElementById('mem-val');
      const cpuB=document.getElementById('cpu-bar'), memB=document.getElementById('mem-bar');
      if(cpuV) cpuV.textContent=`${cpu}%`; if(memV) memV.textContent=`${ram}%`;
      if(cpuB) cpuB.style.width=`${cpu}%`; if(memB) memB.style.width=`${ram}%`;
      const procs = msg.processes as any[];
      if(procs?.length) {
        const sa=document.getElementById('sys-architecture');
        if(sa){ let h=`<div style="font-weight:bold;letter-spacing:2px;border-bottom:1px solid rgba(0,191,255,0.3);padding-bottom:6px;margin-bottom:8px;">ACTIVE PROCESSES</div><pre style="font-family:monospace;margin:0;color:rgba(0,255,136,0.8);font-size:10px;line-height:1.4;">`;
          procs.forEach(p=>{ h+=`${p.name.slice(0,14).padEnd(15)} ${p.cpu}\n`; }); h+=`</pre>`; sa.innerHTML=h; }
      }
    } else if (type==='audio' && msg.data) {
      setState('speaking'); audio.enqueue(msg.data as string);
    } else if (type==='stt_error') {
      resetVoiceWatchdog();
      const errMsg = (msg.message as string) || 'STT TRANSCRIPTION FAILED';
      console.warn(`[Voice Pipeline] Backend STT error received: ${errMsg}`);
      appendHudLog('STT_ERROR', errMsg, '#ff3300');
      errEl.innerText = errMsg;
      errEl.style.opacity = '1';
      setTimeout(() => { errEl.style.opacity = '0'; }, 6000);
      setState('idle');
    } else if (type==='transcript_result') {
      resetVoiceWatchdog();
      if (msg.text) {
        console.log(`[Voice Pipeline] HUD received transcript_result: "${msg.text}" (${msg.engine || 'faster-whisper'}, ${Math.round((msg.latency_ms as number) || 0)}ms)`);
        appendHudLog('STT_TRANSCRIPT', `[${msg.engine || 'faster-whisper'}] "${msg.text}" (${Math.round((msg.latency_ms as number) || 0)}ms)`, '#00ff88');
        statusEl.innerText = `"${msg.text}"`;
      } else {
        console.log(`[Voice Pipeline] HUD received empty transcript.`);
        appendHudLog('STT_EMPTY', "DIDN'T CATCH THAT — TRY AGAIN", '#ffaa00');
        statusEl.innerText = "DIDN'T CATCH THAT — TRY AGAIN";
        errEl.innerText = "DIDN'T CATCH THAT — TRY AGAIN";
        errEl.style.opacity = '1';
        setTimeout(() => { errEl.style.opacity = '0'; }, 3500);
        setState('idle');
      }
    } else if (type === 'chat_stream_start') {
      resetVoiceWatchdog();
      setState('speaking');
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.innerText = '';
      }
    } else if (type === 'token' && msg.token) {
      if (statusEl) {
        statusEl.style.display = 'block';
        const cur = (statusEl.innerText || '') + (msg.token as string);
        statusEl.innerText = cur.replace(/\[TRIGGER_SKILL:[^\]]*\]?/g, '');
      }
    } else if (type === 'chat_stream_end') {
      resetVoiceWatchdog();
      if (msg.full_text) {
        appendHudLog('JARVIS', String(msg.full_text), '#00e5ff');
      }
      if (statusEl && msg.full_text) {
        statusEl.innerText = String(msg.full_text);
        setTimeout(() => {
          if (state === 'idle') statusEl.style.display = 'none';
        }, 6000);
      }
    } else if (type === 'ai_metrics') {
      const reasonStr = msg.fallback_reason ? ` | ${msg.fallback_reason}` : '';
      const info = `[${msg.model}] TTFT: ${msg.time_to_first_token_ms}ms | Total: ${msg.total_time_ms}ms${reasonStr}`;
      console.log(`[AI Metrics] ${info}`);
      appendHudLog('AI_BRAIN', info, '#00ff88');

      // Update HUD active model badge in Stark Diagnostics
      const perfModelEl = document.getElementById('perf-model-val');
      if (perfModelEl && msg.model) {
        const shortModel = String(msg.model).split('(')[0].trim().toUpperCase() + ' FLASH';
        perfModelEl.innerText = shortModel;
        perfModelEl.title = `Active Model: ${msg.model}\nRouting Note: ${msg.fallback_reason || 'Primary active'}`;
      }
    } else if (type === 'confirmation_result') {
      const cardContainer = document.getElementById('hud-card-container');
      if (cardContainer) cardContainer.style.display = 'none';
      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.innerText = msg.status === 'confirmed' ? '✓ Action Confirmed & Executing' : '✕ Action Cancelled';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3500);
    } else if (type==='status' && msg.state) {
      if (msg.state==='idle') {
        resetVoiceWatchdog();
        if (audio.isIdle()) setState('idle');
      }
      else if (msg.state==='transcribing') setState('transcribing');
      else if (msg.state==='thinking') setState('thinking');
      else if (msg.state==='executing') setState('executing');
      else if (msg.state==='working') { setState('thinking'); statusEl.innerText='WORKING...'; }
    } else if (type==='process_update' && msg.message) {
      if (hudOverlay.style.display==='none') triggerBuildHUD();
      appendHudLog('STARK COMPILER', String(msg.message), '#33ff66');
      const lm=String(msg.message).toLowerCase();
      if(lm.includes('analyzing')) setAgentStatus('architect','thinking','Analyzing...',50);
      else if(lm.includes('generating')) { setAgentStatus('architect','success','Blueprint locked.',100); setAgentStatus('ui','active','Compiling...',60); }
      else if(lm.includes('writing')) { setAgentStatus('ui','success','Assets assembled.',100); setAgentStatus('backend','active','Endpoints ready.',80); }
      else if(lm.includes('error')||lm.includes('failed')) setAgentStatus('debug','error','Compiler error.',100);
    } else if (type==='build_complete' && msg.url) {
      preview.show(msg.url as string); completeBuildHUD(msg.url as string);
    } else if (type==='build_failed') {
      clearInterval(progInterval);
      hudProgFill.style.width='100%'; hudProgFill.style.background='linear-gradient(90deg,#ff3300,#ff0055)';
      hudProgPct.textContent='ERROR'; hudProgText.textContent='COMPILATION FAILED';
      setAgentStatus('debug','error','Fatal exception.',100);
      hudCloseBtn.style.display='block'; hudCloseBtn.textContent='[ DISMISS & RECOVER ]';
      hudCloseBtn.onclick=()=>{ hudOverlay.style.display='none'; archViz.stop(); setState('idle'); };
      synth.playWarning();
    } else if ((type==='browser_speak' || type==='browser_speak_chunk') && msg.text) {
      const txt=msg.text as string;
      if (type === 'browser_speak') window.speechSynthesis.cancel();
      const doSpeak=(voices: SpeechSynthesisVoice[])=>{
        const utt=new SpeechSynthesisUtterance(txt);
        const v=voices.find(v=>v.lang==='en-IN'&&!v.name.includes('Female'))||voices.find(v=>v.lang.startsWith('en')&&v.name.includes('Daniel'))||voices.find(v=>v.lang.startsWith('en'))||voices[0];
        if(v) utt.voice=v; utt.lang='en-IN'; utt.rate=1.05; utt.pitch=0.9; utt.volume=1;
        setState('speaking'); utt.onend=()=>setState('idle'); utt.onerror=()=>setState('idle');
        window.speechSynthesis.speak(utt);
        const wd=setTimeout(()=>setState('idle'),15000); utt.onend=()=>{ clearTimeout(wd); setState('idle'); };
      };
      const vs=window.speechSynthesis.getVoices();
      if(vs.length>0) doSpeak(vs); else { window.speechSynthesis.onvoiceschanged=()=>{ doSpeak(window.speechSynthesis.getVoices()); window.speechSynthesis.onvoiceschanged=null; }; }

    } else if (type==='task_complete'||type==='action_queued') {
      const toast=document.createElement('div'); toast.className='toast';
      toast.innerText=type==='action_queued'?`→ ${msg.action}`:`✓ ${msg.name} done`;
      document.body.appendChild(toast); setTimeout(()=>toast.remove(),3000);
    } else if (type==='tts_fallback') {
      errEl.innerText=String(msg.message); errEl.style.opacity='1'; setTimeout(()=>errEl.style.opacity='0',4000);
    } else if (type === 'hud_card' && msg.card) {
      const card = msg.card as any;
      const cardContainer = document.getElementById('hud-card-container');

      if (card.type === 'confirmation') {
        if (cardContainer) {
          const d = card.data || {};
          const confId = card.id || d.id;
          const targetCmd = card.command || d.command || 'Command';
          const skillLabel = card.skill || d.skill || 'System Action';

          const contentHtml = `<div style="background:rgba(20,5,5,0.95);border:1.5px solid #ff4444;border-radius:10px;padding:16px 22px;min-width:360px;backdrop-filter:blur(14px);box-shadow:0 0 35px rgba(255,50,50,0.45);color:#fff;font-family:'Orbitron',sans-serif;">
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,80,80,0.4);padding-bottom:8px;margin-bottom:12px;">
              <div style="font-size:12px;letter-spacing:2px;font-weight:bold;color:#ff5555;">⚠️ SECURITY CONFIRMATION</div>
              <span style="font-size:10px;color:rgba(255,150,150,0.8);">${skillLabel}</span>
            </div>
            <div style="font-size:13px;line-height:1.6;margin-bottom:14px;">
              Run: <code style="background:rgba(255,255,255,0.12);color:#00BFFF;padding:3px 8px;border-radius:4px;font-family:monospace;font-size:12px;">${targetCmd}</code> ?
            </div>
            <div style="font-size:10px;color:rgba(255,255,255,0.5);margin-bottom:14px;letter-spacing:1px;">
              AI attempted to trigger a sensitive system action. User authorization required.
            </div>
            <div style="display:flex;gap:12px;justify-content:flex-end;">
              <button id="cancel-conf-btn-${confId}" style="background:rgba(255,50,50,0.2);border:1px solid #ff4444;color:#ff6666;font-family:'Orbitron';font-size:11px;padding:8px 18px;border-radius:4px;cursor:pointer;">[ CANCEL ]</button>
              <button id="ok-conf-btn-${confId}" style="background:#00ff88;border:none;color:#000;font-family:'Orbitron';font-size:11px;font-weight:bold;padding:8px 22px;border-radius:4px;cursor:pointer;box-shadow:0 0 15px rgba(0,255,136,0.4);">[ CONFIRM ]</button>
            </div>
          </div>`;

          cardContainer.innerHTML = contentHtml;
          cardContainer.style.display = 'block';

          const okBtn = document.getElementById(`ok-conf-btn-${confId}`);
          const cancelBtn = document.getElementById(`cancel-conf-btn-${confId}`);

          if (okBtn) {
            okBtn.onclick = () => {
              cardContainer.style.display = 'none';
              socket.send({ type: 'confirm_action', id: confId, confirmed: true });
            };
          }
          if (cancelBtn) {
            cancelBtn.onclick = () => {
              cardContainer.style.display = 'none';
              socket.send({ type: 'confirm_action', id: confId, confirmed: false });
            };
          }
        }
        return;
      }

      if (card.type === 'music_control') {
        const iframe = document.getElementById('yt-player-iframe') as HTMLIFrameElement;
        if (iframe && iframe.contentWindow) {
          const act = card.data?.action;
          if (act === 'pause') {
            iframe.contentWindow.postMessage('{"event":"command","func":"pauseVideo","args":[]}', '*');
          } else if (act === 'play' || act === 'resume' || act === 'next') {
            iframe.contentWindow.postMessage('{"event":"command","func":"playVideo","args":[]}', '*');
          }
        }
      }

      if (cardContainer) {
        cardContainer.style.display = 'block';
        let contentHtml = `<div style="background:rgba(0,11,24,0.95);border:1px solid #00BFFF;border-radius:10px;padding:14px 20px;min-width:340px;backdrop-filter:blur(12px);box-shadow:0 0 25px rgba(0,191,255,0.4);color:#00BFFF;font-family:'Orbitron',sans-serif;">
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(0,191,255,0.4);padding-bottom:6px;margin-bottom:8px;">
            <div style="font-size:12px;letter-spacing:2px;font-weight:bold;">${card.title || 'JARVIS MEDIA PLAYER'}</div>
            <button onclick="document.getElementById('hud-card-container').style.display='none'" style="background:none;border:none;color:#00BFFF;cursor:pointer;font-size:14px;">✕</button>
          </div>`;

        if (card.type === 'weather') {
          const d = card.data;
          contentHtml += `<div style="display:flex;justify-content:space-between;align-items:center;margin:8px 0;">
            <span style="font-size:32px;font-weight:bold;color:#fff;">${d.temp}</span>
            <div style="text-align:right;font-size:11px;color:rgba(0,191,255,0.8);"><div>${d.condition}</div><div>Humidity: ${d.humidity}</div></div>
          </div>`;
          if (d.forecast?.length) {
            contentHtml += `<div style="font-size:10px;display:flex;gap:12px;margin-top:8px;border-top:1px dashed rgba(0,191,255,0.3);padding-top:6px;">`;
            d.forecast.forEach((f: any) => {
              contentHtml += `<div><div>${f.date}</div><div style="color:#fff;">${f.max_temp}° / ${f.min_temp}°</div></div>`;
            });
            contentHtml += `</div>`;
          }
        } else if (card.type === 'music') {
          const d = card.data;
          const vidId = d.video_id || 'UDVtMYqUAyw';
          contentHtml += `<div style="text-align:center;margin:8px 0;">
            <div style="font-size:13px;font-weight:bold;color:#fff;margin-bottom:2px;">🎵 ${d.title || 'Music Track'}</div>
            <div style="font-size:10px;color:rgba(0,191,255,0.7);margin-bottom:8px;">${d.uploader || 'YouTube Media'}</div>
            <div style="width:100%;height:180px;margin:8px 0;border-radius:6px;overflow:hidden;background:#000;border:1px solid rgba(0,191,255,0.4);position:relative;">
              <iframe id="yt-player-iframe" width="100%" height="180" src="https://www.youtube.com/embed/${vidId}?enablejsapi=1&autoplay=1&origin=${encodeURIComponent(location.origin)}" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>
            </div>
            <button id="tap-to-play-btn" onclick="const iframe=document.getElementById('yt-player-iframe'); if(iframe && iframe.contentWindow){ iframe.contentWindow.postMessage('{\\\"event\\\":\\\"command\\\",\\\"func\\\":\\\"playVideo\\\",\\\"args\\\":[]}','*'); } this.style.display='none';" style="background:#00BFFF;color:#000;font-weight:bold;font-size:11px;padding:8px 14px;border-radius:4px;border:none;cursor:pointer;margin:6px auto;display:block;box-shadow:0 0 12px #00BFFF;font-family:'Orbitron';">▶ TAP TO PLAY AUDIO</button>
            <div style="display:flex;gap:6px;justify-content:center;margin-top:8px;flex-wrap:wrap;">
              <button id="play-pause-btn" onclick="const iframe=document.getElementById('yt-player-iframe'); if(iframe && iframe.contentWindow){ iframe.contentWindow.postMessage('{\\\"event\\\":\\\"command\\\",\\\"func\\\":\\\"playVideo\\\",\\\"args\\\":[]}','*'); }" style="background:rgba(0,255,136,0.2);border:1px solid #00ff88;color:#00ff88;font-size:10px;padding:5px 10px;border-radius:4px;cursor:pointer;font-family:'Orbitron';">▶ PLAY</button>
              <button onclick="const iframe=document.getElementById('yt-player-iframe'); if(iframe && iframe.contentWindow){ iframe.contentWindow.postMessage('{\\\"event\\\":\\\"command\\\",\\\"func\\\":\\\"pauseVideo\\\",\\\"args\\\":[]}','*'); }" style="background:rgba(0,191,255,0.2);border:1px solid #00BFFF;color:#00BFFF;font-size:10px;padding:5px 10px;border-radius:4px;cursor:pointer;font-family:'Orbitron';">⏸ PAUSE</button>
              <button onclick="const iframe=document.getElementById('yt-player-iframe'); if(iframe && iframe.contentWindow){ try{ iframe.contentWindow.postMessage('{\\\"event\\\":\\\"command\\\",\\\"func\\\":\\\"pauseVideo\\\",\\\"args\\\":[]}','*'); }catch(e){} } window.open('${d.url}','_blank');" style="background:rgba(255,200,0,0.2);border:1px solid #ffc800;color:#ffc800;font-size:10px;padding:5px 10px;border-radius:4px;cursor:pointer;font-family:'Orbitron';">↗ BROWSER</button>
            </div>
          </div>`;

        } else if (card.type === 'skills_manifest') {
          contentHtml += `<div style="font-size:11px;line-height:1.6;font-family:monospace;">`;
          card.data.forEach((s: any) => {
            contentHtml += `<div style="margin-bottom:6px;"><strong style="color:#00ff88;">⚡ ${s.name}</strong>: ${s.description}</div>`;
          });
          contentHtml += `</div>`;
        } else {
          contentHtml += `<div style="font-size:11px;font-family:monospace;color:#fff;">${JSON.stringify(card.data, null, 2)}</div>`;
        }

        contentHtml += `</div>`;
        cardContainer.innerHTML = contentHtml;
        setTimeout(() => { cardContainer.style.display = 'none'; }, 25000);
      }
    } else if (type==='phone_event') {
      const ev=msg as any, phoneHud=document.getElementById('phone-call-hud')!;
      if(ev.event==='incoming_call'){ document.getElementById('phone-caller-id')!.textContent=ev.caller; document.getElementById('phone-status')!.textContent='RINGING...'; phoneHud.style.display='block'; synth.playWarning(); }
      else if(ev.event==='end_call'){ document.getElementById('phone-status')!.textContent='DISCONNECTED'; setTimeout(()=>phoneHud.style.display='none',2000); }
    }
  });

  // Global Audio Unlock Listener on user gesture anywhere on HUD
  window.addEventListener('click', () => {
    const iframe = document.getElementById('yt-player-iframe') as HTMLIFrameElement;
    if (iframe && iframe.contentWindow) {
      try {
        iframe.contentWindow.postMessage('{"event":"command","func":"playVideo","args":[]}', '*');
      } catch (e) {}
    }
  }, { once: true });

  // ── Skills Panel Toggle ───────────────────────────────────────────────────
  const btnSkills = document.getElementById('btn-skills');
  const skillsPanel = document.getElementById('skills-panel');
  const closeSkillsBtn = document.getElementById('close-skills-btn');
  const skillsListContainer = document.getElementById('skills-list-container');

  async function loadSkillsManifest() {
    try {
      const res = await authFetch('/api/skills');
      const data = await res.json();
      if (skillsListContainer && data.skills) {
        let html = '';
        data.skills.forEach((s: any) => {
          html += `<div style="border-bottom:1px solid rgba(0,191,255,0.2);padding-bottom:8px;">
            <div style="font-family:'Orbitron',sans-serif;font-size:12px;color:#00ff88;font-weight:bold;">⚡ ${s.name}</div>
            <div style="color:rgba(0,191,255,0.8);font-size:10px;margin:2px 0;">${s.description}</div>
            <div style="color:rgba(0,191,255,0.5);font-size:9px;">Triggers: ${s.triggers.slice(0, 4).join(', ')}</div>
          </div>`;
        });
        skillsListContainer.innerHTML = html;
      }
    } catch (e) {
      if (skillsListContainer) skillsListContainer.innerHTML = 'Failed to load skills.';
    }
  }

  btnSkills?.addEventListener('click', () => {
    if (skillsPanel) {
      const isVisible = skillsPanel.style.display === 'flex';
      skillsPanel.style.display = isVisible ? 'none' : 'flex';
      if (!isVisible) loadSkillsManifest();
    }
  });

  closeSkillsBtn?.addEventListener('click', () => {
    if (skillsPanel) skillsPanel.style.display = 'none';
  });

  // ── Mobile Tap-to-Talk Button ─────────────────────────────────────────────
  const mobileMicBtn = document.getElementById('mobile-mic-btn');
  mobileMicBtn?.addEventListener('click', () => {
    setState('listening');
    voice.start();
    synth.playSweep();
  });


  // ── Panel switcher (gesture support) ──────────────────────────────────────
  const panels = ['left-panels','right-panels'];
  let activePanelSet = 0;
  function switchPanel(dir: number) {
    activePanelSet = (activePanelSet + dir + panels.length) % panels.length;
    panels.forEach((id,i)=>{ const el=document.getElementById(id); if(el) el.style.opacity=i===activePanelSet?'1':'0.3'; });
  }

  // ── Chat input ─────────────────────────────────────────────────────────────
  const chatInput = document.getElementById('chat-input') as HTMLInputElement;
  chatInput.addEventListener('keydown', e => {
    if (e.key==='Enter' && chatInput.value.trim()) {
      const q=chatInput.value.trim();
      socket.send({type:'transcript',text:q,isFinal:true});
      chatInput.value=''; setState('thinking');
      // Record keystroke for emotion engine
      authFetch('/api/emotion').catch(()=>{});
    }
    // Keystroke tracking for emotion
    synth.playTyping();
  });

  // ── Menu ───────────────────────────────────────────────────────────────────
  const btnMenu=document.getElementById('btn-menu')!, menuEl=document.getElementById('menu-dropdown')!;
  btnMenu.addEventListener('click',e=>{ e.stopPropagation(); menuEl.style.display=menuEl.style.display==='none'?'flex':'none'; });
  document.addEventListener('click',()=>menuEl.style.display='none');
  document.getElementById('btn-restart')?.addEventListener('click',()=>{ authFetch('/api/restart',{method:'POST'}); errEl.innerText='Restarting...'; errEl.style.opacity='1'; setTimeout(()=>location.reload(),4000); });
  document.getElementById('btn-fix-self')?.addEventListener('click',()=>socket.send({type:'fix_self'}));
  document.getElementById('close-sidebar')?.addEventListener('click',()=>preview.hide());


  // Phone accept
  document.getElementById('phone-accept-btn')?.addEventListener('click',()=>{ socket.send({type:'answer_call'}); synth.playSuccess(); });

  // Persona switcher
  const personaSel=document.getElementById('persona-select') as HTMLSelectElement;
  personaSel?.addEventListener('change',e=>{
    const mode=(e.target as HTMLSelectElement).value;
    const colors: Record<string,string>={architect:'#00BFFF',hacker:'#00ff88',creative:'#ff00ff',tactical:'#ff4400'};
    const color=colors[mode]||'#00BFFF';
    document.body.style.filter='contrast(1.5) blur(2px) hue-rotate(90deg)';
    setTimeout(()=>document.body.style.filter='none',150);
    setTimeout(()=>document.body.style.filter='contrast(2) blur(1px) hue-rotate(-90deg)',200);
    setTimeout(()=>document.body.style.filter='none',300);
    document.documentElement.style.setProperty('--primary-cyan',color);
    const utt=new SpeechSynthesisUtterance(`Switching to ${mode} mode.`); utt.rate=1.2; window.speechSynthesis.speak(utt);
  });

  // Neural bars
  const neuralBarsEl=document.getElementById('neural-bars');
  const neuralBars: HTMLDivElement[]=[];
  if(neuralBarsEl){ for(let i=0;i<35;i++){ const w=document.createElement('div'); w.style.cssText='flex:1;height:100%;display:flex;align-items:flex-end;'; const b=document.createElement('div'); b.className='neural-bar-fill'; b.style.height=Math.random()*100+'%'; w.appendChild(b); neuralBarsEl.appendChild(w); neuralBars.push(b); } }
  let animT=0, lastNT=0;
  const neuralLoop=(now:number)=>{ if(now-lastNT>120){ lastNT=now; animT+=0.08; const intensity=state==='thinking'?2.2:1.0; neuralBars.forEach((b,i)=>{ let v=Math.abs(Math.sin(animT*2+i*0.3)*45*intensity)+Math.random()*18*intensity; if(v>100)v=100; b.style.height=v+'%'; b.style.backgroundColor=state==='thinking'?'#00ff88':'rgba(0,191,255,0.7)'; }); const loadEl=document.getElementById('neural-load'); if(loadEl) loadEl.textContent=String(Math.round(neuralBars.reduce((s,b)=>s+parseFloat(b.style.height),0)/neuralBars.length)); } requestAnimationFrame(neuralLoop); };
  requestAnimationFrame(neuralLoop);

  // Meeting scribe
  const meetBtn=document.getElementById('meeting-toggle-btn')!, meetStatus=document.getElementById('meeting-status')!, meetBody=document.getElementById('meeting-scribe-body')!;
  let meetActive=false, meetRec: any=null;
  meetBtn?.addEventListener('click',()=>{
    meetActive=!meetActive;
    if(meetActive){ meetBtn.textContent='STOP SCRIBE'; meetStatus.textContent='RECORDING'; meetStatus.className='agent-status active'; meetBody.innerHTML='<div style="color:#00ff88">[SYSTEM] Recording...</div>'; synth.playSweep();
      const SR=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
      if(SR){ meetRec=new SR(); meetRec.continuous=true; meetRec.interimResults=true; meetRec.lang='en-US';
        meetRec.onresult=(ev:any)=>{ let t=''; for(let i=ev.resultIndex;i<ev.results.length;++i) if(ev.results[i].isFinal) t+=' '+ev.results[i][0].transcript; if(t.trim()){ const d=document.createElement('div'); d.style.color='#fff'; d.style.marginBottom='4px'; d.textContent=`• ${t.trim()}`; meetBody.appendChild(d); meetBody.scrollTop=meetBody.scrollHeight; } };
        meetRec.start(); }
    } else { meetBtn.textContent='START SCRIBE'; meetStatus.textContent='STANDBY'; meetStatus.className='agent-status'; if(meetRec){ meetRec.stop(); meetRec=null; } synth.playSuccess(); }
  });

  // ── Workspace File Explorer ───────────────────────────────────────────────
  const refreshBtn = document.getElementById('refresh-workspace')!;
  
  async function openFilePreview(path: string) {
    const sidebar = document.getElementById('process-sidebar')!;
    const liveCode = document.getElementById('live-code')!;
    const previewFrame = document.getElementById('preview-frame') as HTMLIFrameElement;
    const processLog = document.getElementById('process-log')!;
    
    sidebar.style.right = '0';
    sidebar.style.width = 'min(70vw, 900px)';
    
    if (previewFrame) previewFrame.style.display = 'none';
    if (processLog) processLog.style.display = 'none';
    liveCode.style.display = 'block';
    liveCode.textContent = 'Loading file contents...';
    
    try {
      const res = await authFetch(`/api/files/content?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      if (data.error) {
        liveCode.textContent = `Error: ${data.error}`;
      } else {
        liveCode.textContent = data.content;
      }
    } catch (err) {
      liveCode.textContent = 'Failed to load file contents.';
    }
  }

  async function loadWorkspaceFiles() {
    const treeEl = document.getElementById('workspace-tree')!;
    if (!treeEl) return;
    try {
      const res = await authFetch('/api/files');
      const data = await res.json();
      if (data.error) {
        treeEl.innerHTML = `<div style="color:#ff3300;padding:5px;">Error: ${data.error}</div>`;
        return;
      }
      treeEl.innerHTML = '';
      
      const renderNode = (node: any, parentEl: HTMLElement, depth = 0) => {
        const item = document.createElement('div');
        item.style.paddingLeft = `${depth * 10}px`;
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.gap = '6px';
        item.style.paddingTop = '2px';
        item.style.paddingBottom = '2px';
        item.style.cursor = 'pointer';
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = node.name;
        
        if (node.type === 'directory') {
          const iconSpan = document.createElement('span');
          iconSpan.textContent = '📁';
          item.appendChild(iconSpan);
          nameSpan.style.color = '#ffaa00';
          item.appendChild(nameSpan);
          
          const childContainer = document.createElement('div');
          childContainer.style.display = 'none';
          
          item.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = childContainer.style.display !== 'none';
            childContainer.style.display = isOpen ? 'none' : 'block';
            iconSpan.textContent = isOpen ? '📁' : '📂';
          });
          
          parentEl.appendChild(item);
          parentEl.appendChild(childContainer);
          
          node.children.forEach((child: any) => {
            renderNode(child, childContainer, depth + 1);
          });
        } else {
          const iconSpan = document.createElement('span');
          iconSpan.textContent = '📄';
          item.appendChild(iconSpan);
          nameSpan.style.color = '#00ff88';
          item.appendChild(nameSpan);
          
          item.addEventListener('click', (e) => {
            e.stopPropagation();
            openFilePreview(node.path);
          });
          
          parentEl.appendChild(item);
        }
      };
      
      data.forEach((node: any) => {
        renderNode(node, treeEl);
      });
    } catch (err) {
      treeEl.innerHTML = `<div style="color:#ff3300;padding:5px;">Failed to fetch workspace tree.</div>`;
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      synth.playSweep();
      loadWorkspaceFiles();
    });
  }
  
  loadWorkspaceFiles();
  setInterval(loadWorkspaceFiles, 8000);

  // ── HUD Visibility Control ────────────────────────────────────────────────
  let hudVisible = false;
  const hudElements = [
    'status-tl', 'status-tr', 'status-bl', 'status-br',
    'left-panels', 'right-panels', 'workspace-sidebar', 'controls'
  ];

  function setHudVisibility(visible: boolean) {
    hudVisible = visible;
    hudElements.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        if (visible) {
          if (id.startsWith('status-')) {
            el.style.display = 'block';
          } else if (id === 'controls' || id === 'left-panels' || id === 'right-panels') {
            el.style.display = 'flex';
          } else {
            el.style.display = 'flex';
          }
          el.style.opacity = '1';
        } else {
          el.style.display = 'none';
        }
      }
    });
    const toggleBtn = document.getElementById('toggle-hud-btn');
    if (toggleBtn) {
      toggleBtn.textContent = visible ? 'HIDE DIAGNOSTIC HUD' : 'SHOW DIAGNOSTIC HUD';
    }
  }

  // Hide by default on initialization
  setHudVisibility(false);

  const toggleHudBtn = document.getElementById('toggle-hud-btn');
  if (toggleHudBtn) {
    toggleHudBtn.addEventListener('click', () => {
      synth.playSweep();
      setHudVisibility(!hudVisible);
    });
  }

  // Automatically show HUD when compilation activity starts
  socket.onMessage((msg) => {
    const type = msg.type as string;
    if (type === 'process_update' || type === 'build_complete' || type === 'build_failed') {
      if (!hudVisible) {
        setHudVisibility(true);
      }
    }
  });

  if(window.speechSynthesis.onvoiceschanged!==undefined) window.speechSynthesis.onvoiceschanged=()=>window.speechSynthesis.getVoices();
}

main();
