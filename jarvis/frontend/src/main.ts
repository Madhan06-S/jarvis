import { createSocket } from './ws';
import { VoiceInput, AudioPlayer } from './voice';
import { createOrb, OrbState } from './orb';

const statusEl = document.getElementById('status-text')!;
const errEl = document.getElementById('error-text')!;

function main() {
    const orb = createOrb(document.getElementById('orb-canvas') as HTMLCanvasElement);
    const audio = new AudioPlayer();
    orb.setAnalyser(audio.getAnalyser());
    audio.ensureUnlocked();

    let state: OrbState = "idle";
    
    let isMuted = false;
    const voice = new VoiceInput((t) => {
        if (isMuted) return;
        audio.stop();
        socket.send({ type: "transcript", text: t, isFinal: true });
        setState("thinking");
    });

    const btnMute = document.getElementById('btn-mute')!;
    btnMute.addEventListener('click', () => {
        isMuted = !isMuted;
        if (isMuted) {
            btnMute.classList.add('muted');
            voice.pause();
        } else {
            btnMute.classList.remove('muted');
            if (state === "listening" || state === "idle") {
                voice.start();
            }
        }
    });

    function setState(s: OrbState) {
        state = s;
        orb.setState(s);
        if (s === "idle") {
            statusEl.innerText = "";
            if (!isMuted) setTimeout(() => voice.start(), 800);
        } else if (s === "listening") {
            statusEl.innerText = "LISTENING";
            if (!isMuted) voice.start();
        } else if (s === "thinking") {
            statusEl.innerText = "THINKING";
            voice.pause();
        } else if (s === "speaking") {
            statusEl.innerText = "SPEAKING";
            voice.pause();
        }
    }

    const wsUrl = `ws://${location.hostname}:8340/ws/voice`;
    const socket = createSocket(wsUrl);

    socket.onConnectionChange(conn => {
        if (conn) {
            errEl.style.opacity = "0";
            setTimeout(() => setState("listening"), 1000);
        } else {
            errEl.innerText = "Reconnecting to JARVIS...";
            errEl.style.opacity = "1";
            voice.pause();
            setState("idle");
        }
    });

    audio.onFinished(() => {
        setState("idle");
    });

    socket.onMessage(msg => {
        if (msg.type === "audio" && msg.data) {
            setState("speaking");
            audio.enqueue(msg.data as string);
        } else if (msg.type === "status" && msg.state) {
            if (msg.state === "idle" && audio.isIdle()) {
                setState("idle");
            } else if (msg.state === "working") {
                setState("thinking");
                statusEl.innerText = "WORKING...";
            }
        } else if (msg.type === "tts_fallback") {
            errEl.innerText = String(msg.message);
            errEl.style.opacity = "1";
            setTimeout(() => { errEl.style.opacity = "0"; }, 4000);
        } else if (msg.type === "task_complete" || msg.type === "action_queued") {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.innerText = msg.type === 'action_queued' ? `→ ${msg.action}` : `✓ ${msg.name} done`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        } else if (msg.type === "process_update" && msg.message) {
            const sidebar = document.getElementById('process-sidebar');
            if (sidebar) sidebar.style.right = "20px";
            const logEl = document.getElementById('process-log');
            if (logEl) {
                const p = document.createElement('div');
                p.innerText = `> ${msg.message}`;
                p.style.marginBottom = "4px";
                logEl.appendChild(p);
                logEl.scrollTop = logEl.scrollHeight;
            }
        } else if (msg.type === "process_complete") {
            // Keep the sidebar open but let the user know it's done
            const logEl = document.getElementById('process-log');
            if(logEl) {
                const p = document.createElement('div');
                p.innerText = '> ✅ PROCESS COMPLETE';
                p.style.color = '#00ff88';
                p.style.fontWeight = 'bold';
                p.style.marginTop = '10px';
                logEl.appendChild(p);
                logEl.scrollTop = logEl.scrollHeight;
            }
        } else if (msg.type === "code_stream_start") {
            const sidebar = document.getElementById('process-sidebar');
            const liveCode = document.getElementById('live-code');
            const iframe = document.getElementById('preview-frame');
            if (sidebar && liveCode && iframe) {
                sidebar.style.right = "20px";
                sidebar.style.width = "45vw";
                sidebar.style.top = "40px";
                sidebar.style.bottom = "40px";
                iframe.style.display = "none";
                liveCode.style.display = "block";
                liveCode.innerText = ""; // Clear previous
            }
        } else if (msg.type === "code_stream_chunk" && typeof msg.text === "string") {
            const liveCode = document.getElementById('live-code');
            if (liveCode) {
                liveCode.innerText += msg.text;
                liveCode.scrollTop = liveCode.scrollHeight;
            }
        } else if (msg.type === "code_stream_end") {
            // Keep it visible until build_complete
        } else if (msg.type === "build_complete" && msg.url) {
            const sidebar = document.getElementById('process-sidebar');
            const logEl = document.getElementById('process-log');
            const liveCode = document.getElementById('live-code');
            const url = msg.url as string;

            // Open in a real new tab — full size
            window.open(url, '_blank');

            // Keep sidebar open with a launch button
            if (sidebar) {
                sidebar.style.right = "20px";
                sidebar.style.width = "320px";
                sidebar.style.top = "80px";
                sidebar.style.bottom = "120px";
                if (logEl) logEl.style.maxHeight = "60%";
                if (liveCode) liveCode.style.display = "none";

                // Add/update launch button
                let btn = document.getElementById('launch-btn');
                if (!btn) {
                    btn = document.createElement('a');
                    btn.id = 'launch-btn';
                    sidebar.appendChild(btn);
                }
                const anchor = btn as HTMLAnchorElement;
                anchor.href = url;
                anchor.target = '_blank';
                anchor.textContent = '🚀 Open ' + url;
                Object.assign(anchor.style, {
                    display: 'block',
                    marginTop: '12px',
                    padding: '12px 16px',
                    background: 'linear-gradient(135deg,#00e5ff,#6366f1)',
                    color: '#000',
                    fontWeight: '800',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    textAlign: 'center',
                    fontSize: '13px',
                    boxShadow: '0 0 16px rgba(0,229,255,0.4)',
                });
            }
        } else if (msg.type === "browser_speak" && msg.text) {
            const speakText = msg.text as string;
            window.speechSynthesis.cancel();

            const doSpeak = (voices: SpeechSynthesisVoice[]) => {
                const utt = new SpeechSynthesisUtterance(speakText);
                const v = voices.find(v => v.lang === "en-IN" && !v.name.includes("Female"))
                    || voices.find(v => v.lang.startsWith("en") && v.name.includes("Daniel"))
                    || voices.find(v => v.lang.startsWith("en") && !v.name.includes("Female"))
                    || voices.find(v => v.lang.startsWith("en"))
                    || (voices.length > 0 ? voices[0] : null);
                if (v) utt.voice = v;
                utt.lang = "en-IN"; utt.rate = 0.95; utt.pitch = 0.85; utt.volume = 1;
                setState("speaking");
                utt.onend = () => setState("idle");
                utt.onerror = (e) => {
                    console.warn("TTS error:", e.error);
                    setState("idle");
                };
                window.speechSynthesis.speak(utt);

                // Chrome bug: SpeechSynthesis can stall on long text — watchdog
                const watchdog = setTimeout(() => setState("idle"), 15000);
                utt.onend = () => { clearTimeout(watchdog); setState("idle"); };
            };

            const voices = window.speechSynthesis.getVoices();
            if (voices.length > 0) {
                doSpeak(voices);
            } else {
                // Voices not yet loaded — wait for them
                window.speechSynthesis.onvoiceschanged = () => {
                    doSpeak(window.speechSynthesis.getVoices());
                    window.speechSynthesis.onvoiceschanged = null;
                };
            }
        }
    });

    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }

    const btnMenu = document.getElementById('btn-menu')!;
    const menuEl = document.getElementById('menu-dropdown')!;
    btnMenu.addEventListener('click', (e) => {
        e.stopPropagation();
        menuEl.style.display = menuEl.style.display === "none" ? "flex" : "none";
    });
    document.addEventListener('click', () => {
        menuEl.style.display = "none";
    });

    const closeSidebarBtn = document.getElementById('close-sidebar');
    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener('click', () => {
            const sidebar = document.getElementById('process-sidebar');
            const iframe = document.getElementById('preview-frame') as HTMLIFrameElement;
            const logEl = document.getElementById('process-log');
            if (sidebar) {
                sidebar.style.right = "-600px";
                setTimeout(() => {
                    sidebar.style.width = "350px";
                    sidebar.style.top = "80px";
                    sidebar.style.bottom = "120px";
                    if (iframe) {
                        iframe.style.display = "none";
                        iframe.src = "about:blank";
                    }
                    if (logEl) {
                        logEl.style.maxHeight = "100%";
                        logEl.innerHTML = "";
                    }
                }, 400); // Wait for transition
            }
        });
    }

    const chatInput = document.getElementById('chat-input') as HTMLInputElement;
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && chatInput.value.trim()) {
            socket.send({ type: "transcript", text: chatInput.value.trim(), isFinal: true });
            chatInput.value = '';
            setState("thinking");
        }
    });

    document.getElementById('btn-restart')!.addEventListener('click', () => {
        fetch('/api/restart', { method: 'POST' });
        errEl.innerText = "Restarting...";
        errEl.style.opacity = "1";
        setTimeout(() => location.reload(), 4000);
    });

    document.getElementById('btn-fix-self')!.addEventListener('click', () => {
        socket.send({ type: "fix_self" });
    });
    
    // Add settings panel click logic later if needed

    // Update CPU/Mem Stats to simulate JARVIS load
    let animT = 0;
    setInterval(() => {
        animT += 0.05;
        const c = 35 + Math.sin(animT * 0.7) * 22;
        const m = 50 + Math.cos(animT * 0.4) * 12;
        document.getElementById("cpu-bar")!.style.width = c.toFixed(0) + "%";
        document.getElementById("cpu-val")!.textContent = c.toFixed(0) + "%";
        document.getElementById("mem-bar")!.style.width = m.toFixed(0) + "%";
        document.getElementById("mem-val")!.textContent = m.toFixed(0) + "%";
        
        // Also update uptime
        const up = performance.now();
        const hrs = Math.floor(up / 3600000).toString().padStart(2, '0');
        const mins = Math.floor((up % 3600000) / 60000).toString().padStart(2, '0');
        const secs = Math.floor((up % 60000) / 1000).toString().padStart(2, '0');
        const uptimeEl = document.getElementById('uptime');
        if (uptimeEl) uptimeEl.innerText = `${hrs}:${mins}:${secs}`;
    }, 2000);
}

main();
