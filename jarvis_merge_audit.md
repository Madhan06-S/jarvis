# JARVIS Feature Merge Audit & Security Review
**Target Project:** Antigravity JARVIS (`/Users/madhan/Downloads/projects/ironnn/jarvis`)  
**Reference Repository:** `adewaskar/jarvis` (Cloned at `_reference/adewaskar-jarvis`)  
**Audit Date:** 2026-10-20  
**Phase:** Phase 1 — Comprehensive Audit & Security Review (Zero Modifications to Active Project)

---

## 1. Executive Summary

This audit assesses the architectural compatibility, feature delta, security posture, and merger feasibility between **your existing JARVIS** (Python FastAPI + WebSocket backend, Anthropic Claude / Google Gemini multi-AI brain, local faster-whisper STT, edge-tts/browser TTS, Three.js/Canvas HUD with cyber defense, biometrics, and modular python skills) and **adewaskar's JARVIS** (Node.js bridge wrapping Anthropic Claude Code Agent SDK, React 19 + Three.js + WebGL GLSL shaders, Kokoro on-device WebGPU neural TTS, MediaPipe hand-tracking, and Claude MCP server integrations).

### Key Findings
1. **Brain & Orchestration:** The reference project runs headless Claude Code via `@anthropic-ai/claude-agent-sdk` executing against local `~/.claude.json` MCP servers and the user's Anthropic billing. Your JARVIS operates on a standalone FastAPI server (`server.py`) with Gemini/Claude direct API integration (`ai_brain.py`) and modular Python skills (`skills/`). **The reference brain architecture should NOT be copied directly.** Instead, the tool ideas, UI controls, audio pipeline, and security proxies should be ported into your Python backend and TypeScript/Three.js frontend.
2. **Security Verdict:** The reference repository is cleanly written, well-documented, and shows exceptionally conscientious security design:
   - Built-in SSRF protection with IP literal blocking and DNS rebinding protection (`guardedLookup`).
   - Strict Content Security Policy (CSP), DOMPurify sanitization with a strict class allowlist for AI-generated HTML panels, and cryptographic nonces on injected reader shims.
   - Default-deny permission gate (`decideTool`) separating read-only queries from effectful actions.
   - **Zero backdoors, obfuscated code, telemetry beacons, or hardcoded API keys.**
   - Minor risks identified: direct access to the local Chrome extension native socket (`/tmp/claude-mcp-browser-bridge-*`) without auth tokens, and browser-side `VITE_ANTHROPIC_API_KEY` in direct mode.
3. **High-Value Merge Candidates (Recommended for Phase 2):**
   - **Voice barge-in & VAD energy gate** (interrupt assistant mid-speech safely without auto-confirming destructive skills).
   - **Multi-tier TTS pipeline** (Kokoro local WebGPU neural TTS + ElevenLabs API fallback + browser speech fallback).
   - **AI-Authored HUD Panels & Blades** (Dynamic UI cards rendered safely via DOMPurify with class allowlist and strict CSP).
   - **Voice-controlled UI Skills** (`ui_theme`, `ui_reactor`, `ui_orbit`, `ui_chrome`, `ui_effect`, `ui_screen`, `ui_reset`).
   - **Safe Media/Web Page Proxy Endpoints** (`/img`, `/media`, `/page` with SSRF gate and bearer token requirement).
   - **Developer Diagnostics Panel ('D') & Audio Self-Test ('T') & Keyboard Shortcuts ('Space', 'Esc', 'V').**
   - **Four-stage Iron Man Boot Sequence** (using Web Audio / royalty-free sounds).
   - **Python Setup Check Script** (`setup_check.py`).

---

## 2. Architectural Comparison

| Dimension | Your Existing JARVIS | adewaskar's JARVIS | Merge Assessment |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python 3.10+ / FastAPI / Uvicorn (Port 8340) | Node.js 20+ / Native `http` & `ws` (Port 8787) | **Keep Yours:** Port new endpoints into FastAPI |
| **AI Brain** | Gemini 2.0/2.5 Flash, Claude 3.5/Sonnet 4, OpenAI GPT-4o, Pollinations fallback (`ai_brain.py`) | Headless Claude Code Agent SDK (`@anthropic-ai/claude-agent-sdk`, Opus 5 / Sonnet 5) | **Keep Yours:** Retain multi-model freedom; skip Agent SDK lock-in |
| **Skill Architecture** | Dynamic auto-discovery in `skills/*_skill.py` (`NAME`, `DESCRIPTION`, `TRIGGERS`, `run()`) | In-process MCP servers (`displayServer`, `uiServer`, `chromeServer`, `visionServer`) | **Keep Yours:** Adapt features as modular skills in `skills/` |
| **Authentication** | 32-byte secure bearer token (`JARVIS_AUTH_TOKEN`), WebSocket subprotocol auth, rate limiting | Origin header check (`isDevPort`), optional `JARVIS_ALLOW_NO_ORIGIN`, no auth token | **Keep Yours:** Enforce your auth token on all new WebSocket and proxy endpoints |
| **Confirmation Gate** | In-app confirmation cards for restricted commands (`RUN_COMMAND`, `REWRITE_CODE`, etc.) | Read-only default deny gate (`decideTool`) with `JARVIS_ALLOW_WRITES=1` env switch | **Keep Yours:** Retain on-screen confirmation cards; align barge-in rules |
| **Frontend Framework** | Vanilla TypeScript + Vite + Three.js (`jarvis/frontend`) | React 19 + TypeScript + Vite + Three.js (`@react-three/fiber`, `@react-three/drei`) | **Hybrid Adaptation:** Implement shaders and HUD components in your Vite/Three.js frontend |
| **Speech-to-Text** | Local `faster-whisper` (16kHz mono PCM via WebSocket) | ElevenLabs Scribe via `/stt` OR Web SpeechRecognition with heartbeat | **Keep Yours + Upgrade:** Keep local whisper, add ElevenLabs fallback |
| **Text-to-Speech** | Edge-TTS + Browser `SpeechSynthesis` | ElevenLabs API via `/tts` + Kokoro WebGPU (82M ONNX) + Browser `SpeechSynthesis` | **Merge:** Add Kokoro and ElevenLabs options |
| **Arc Reactor UI** | 2D Canvas procedurally animated rings and particles (`orb.ts`) | 3D WebGL GLSL polar shader plane (`Core.tsx`, fbm turbulence, erosion, radar sweep) | **Merge:** Port GLSL shader and orbiting textures to `orb.ts` |

---

## 3. Complete Feature Inventory & Classification

Features are classified as:
- **NEW**: Capabilities not currently present in your JARVIS.
- **BETTER**: Capabilities where the reference implementation is technically or ergonomically superior.
- **DUPLICATE**: Capabilities already present and working in your JARVIS.
- **SKIP**: Unsafe, out of scope, or incompatible architecture.

| Feature Name | What It Does | Reference Implementation File | Dependencies & API Keys | Your Equivalent | Verdict | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Barge-In Voice Interruption** | Voice activity instantly cuts assistant speech playback mid-sentence and resets state without dropping audio frames | `src/lib/vad.ts`, `src/lib/voice.ts`, `src/lib/tts.ts` | None (Web Audio API) | None (currently linear turn wait) | **NEW** | **Merge:** Add to `voice.ts` in frontend. Safety rule: speech during barge-in must NEVER confirm restricted cards. |
| **Local Energy VAD** | Real-time microphone RMS energy floor tracking with hysteresis and onset buffering | `src/lib/vad.ts` | None (Web Audio API) | Custom ScriptProcessor in `voice.ts` | **BETTER** | **Merge:** Replace naive silence timeout with their adaptive noise-floor and attack detector. |
| **Kokoro Local Neural TTS** | High-fidelity 82M parameter British male voices running 100% on-device via WebGPU ONNX | `src/lib/kokoro.ts` | `kokoro-js`, WebGPU browser support | Edge-TTS / Web SpeechSynthesis | **BETTER** | **Merge:** Add as client-side neural voice option (`bm_george`, `bm_fable`, `bm_lewis`, `bm_daniel`). |
| **ElevenLabs Cloud TTS Proxy** | Server-side ElevenLabs streaming TTS with automatic fallback to browser voice | `bridge/server.mjs`, `src/lib/tts.ts` | `ELEVENLABS_API_KEY`, ElevenLabs REST API | Basic ElevenLabs config in `server.py` | **BETTER** | **Merge:** Wire into server with streaming latency optimization `optimize_streaming_latency=3`. |
| **Capability Detection (`/health`)** | Bridge reports available STT/TTS capabilities at boot; frontend configures itself dynamically | `bridge/server.mjs`, `src/lib/capabilities.ts` | None | None | **NEW** | **Merge:** Add `/health` endpoint to `server.py` returning engine status. |
| **Voice-Controlled Theme (`ui_theme`)** | Spoken commands change global accent color, background hue, and phase palettes | `bridge/ui.mjs`, `src/store.ts` | None | None | **NEW** | **Merge:** Implement as `theme_skill.py` communicating via WebSocket to frontend. Store in `localStorage`. |
| **Voice-Controlled Reactor (`ui_reactor`)** | Spoken commands adjust reactor color, scale, glow intensity, spin rate, and styles (`ring`, `sphere`, `wire`) | `bridge/ui.mjs`, `src/scene/Core.tsx` | Three.js / GLSL | None (fixed canvas orb) | **NEW** | **Merge:** Implement as `reactor_skill.py`. Update `orb.ts` to support scale, spin, and style switches. |
| **Orbiting Image Shelf (`ui_orbit`)** | Places generated renders or screenshots in a 3D tilted orbit revolving around the reactor | `bridge/ui.mjs`, `src/scene/Orbits.tsx` | Three.js | None | **NEW** | **Merge:** Add `orbit_skill.py` and 3D textured orbit plane in Three.js frontend. |
| **HUD Chrome Visibility (`ui_chrome`)** | Dynamically toggle rails, conversation transcript, tool badges, and brand watermark | `bridge/ui.mjs`, `src/store.ts` | None | None | **NEW** | **Merge:** Add `chrome_skill.py` to allow distraction-free or focus modes. |
| **Interface Flourishes (`ui_effect`)** | Triggers one-off CSS screen animations (`glitch`, `pulse`, `scan`, `shake`, `flash`) | `bridge/ui.mjs`, `src/ui/Effects.tsx` | CSS Keyframes | None | **NEW** | **Merge:** Add `effects_skill.py` with corresponding CSS keyframes in `style.css`. |
| **Clear / Reset Screen (`ui_screen`, `ui_reset`)** | Clears panels/transcripts or resets all UI customizations back to stock Iron Man cyan | `bridge/ui.mjs`, `src/store.ts` | None | None | **NEW** | **Merge:** Add `screen_reset_skill.py` to restore baseline appearance. |
| **AI-Authored HUD Panels (`display`)** | AI generates customized HTML cards rendered within a fixed `.hud-*` design system | `bridge/panels.mjs`, `src/ui/Panels.tsx` | `dompurify` | Fixed card templates (`hud-panels.ts`) | **BETTER** | **Merge:** Add `display_panel` skill with strict DOMPurify class allowlist and CSP enforcement. |
| **Full-Surface Blades (`blade`)** | Deep-reading surface for articles, photo galleries, video players, and live dashboards | `bridge/panels.mjs`, `src/ui/Blades.tsx` | DOMPurify, CSS | None | **NEW** | **Merge:** Support expandable reading blades on the HUD alongside compact cards. |
| **SSRF-Guarded Media Proxy (`/img`, `/media`)** | Server-side proxy fetching remote images and video to prevent IP leaking and bypass hotlink bans | `bridge/server.mjs`, `bridge/net.mjs` | Node http/https (Python `httpx` for port) | None | **NEW** | **Merge:** Add authenticated `/img` and `/media` endpoints in `server.py` with strict SSRF filtering. |
| **SSRF-Guarded Reader Proxy (`/page`)** | Server-side page scraper extracting prose, stripping scripts, and serving sanitized reader view | `bridge/server.mjs`, `bridge/page.mjs` | None | None | **NEW** | **Merge:** Add `/page` endpoint in `server.py` rendering clean article mode in iframe. |
| **URL Inspector (`probe_url`)** | Pre-flight probe checking content-type, status, prose length, and lead image before displaying | `bridge/panels.mjs`, `bridge/page.mjs` | None | None | **NEW** | **Merge:** Include helper in Python backend for intelligent URL rendering. |
| **Browser Diagnostics Panel ('D')** | Overlay HUD stating hearing status, mic RMS level, TTS engine, session count, and failure reasons | `src/ui/Diagnostics.tsx` | None | None | **NEW** | **Merge:** Bind key 'D' to toggle diagnostics HUD overlay in frontend. |
| **One-Line Audio Test ('T')** | Shortcut 'T' triggers an immediate synthesized test phrase with diagnostic output | `src/App.tsx`, `src/ui/Diagnostics.tsx` | None | None | **NEW** | **Merge:** Bind key 'T' for instant audio loopback verification. |
| **Voice Cycler ('V')** | Shortcut 'V' cycles through installed operating system TTS voices and speaks a sample | `src/App.tsx`, `src/lib/tts.ts` | Web Speech API | None | **NEW** | **Merge:** Bind key 'V' in frontend to audition and persist voice choice. |
| **PTT / Stand Down Shortcuts** | Space = talk without wake word; Escape = stand down/interrupt speech | `src/App.tsx` | None | Partial (mic button click) | **BETTER** | **Merge:** Add global keyboard event listeners in `frontend/src/main.ts`. |
| **Iron Man 4-Beat Boot Sequence** | Start sequence: Status bar log -> Reticle rings -> Suit schematic -> Arc reactor lighting | `src/ui/Boot.tsx` | SVG, CSS animations | Gate screen / Electron main window | **BETTER** | **Merge:** Add SVG 4-beat boot overlay to `frontend/index.html`. Use custom Web Audio sounds. |
| **Interactive Hand Tracking** | MediaPipe 21-joint skeleton tracking via webcam, 1€ smoothing filter, pinch-to-click | `src/lib/hands.ts`, `src/ui/Pointer.tsx` | `@mediapipe/tasks-vision`, WebAssembly | `gesture_control.py` (server-side OpenCV) | **BETTER** | **Merge (Optional/Later):** Client-side WebAssembly tracking is faster and lower latency than OpenCV over WS. |
| **Webcam Vision Tools (`look`, `watch`)** | Assistant takes webcam frame snapshot or contact sheet grid to analyze visual user context | `bridge/vision.mjs`, `src/lib/camera.ts` | MediaDevices API | `face_security.py` (local OpenCV) | **BETTER** | **Merge:** Implement as vision skill using client-side frame capture with on-screen indicator. |
| **Clap-to-Wake Detection** | Transient audio attack detector initiating boot on physical clap | `src/lib/clap.ts` | Web Audio API Analyser | None | **NEW** | **Optional:** Add as novelty ignition method. |
| **Procedural Web Audio SFX** | Pure synthesizer audio cues (boot, wake, listen, tool, done, error) with no external MP3 dependencies | `src/lib/sfx.ts` | Web Audio API | Audio element playback | **BETTER** | **Merge:** Embed zero-dependency Web Audio synthesizers for UI beeps. |
| **Chrome Extension Socket Control** | Connects to `/tmp/claude-mcp-browser-bridge-<user>` Unix socket to drive user's live Chrome browser | `bridge/chrome.mjs` | Local Chrome extension socket | `browser.py` (Playwright automation) | **SKIP / CAUTION** | **Skip / Use Playwright:** The Chrome native socket relies on Anthropic's closed extension. Use Playwright with confirmation cards instead. |
| **Headless Claude Agent SDK Brain** | Spawns headless `claude` CLI and delegates orchestration to Anthropic SDK | `bridge/server.mjs` | `@anthropic-ai/claude-agent-sdk` | Multi-model brain (`ai_brain.py`) | **SKIP** | **Skip:** Incompatible with your Python multi-LLM architecture and requires Claude Code subscription. |
| **MCP Server Config Loader** | Parses `~/.claude.json` to expose all installed MCP servers | `bridge/server.mjs` | Local filesystem | Custom skill loader in `intent_router.py` | **SKIP** | **Skip in Phase 1;** add standalone MCP client protocol to Python in Phase 3. |
| **Default-Deny Permission Gate** | Filters MCP tool calls by regex verb allowlists and blocks writes unless enabled | `bridge/server.mjs` (`decideTool`) | None | Confirmation cards in `server.py` | **DUPLICATE** | **Keep Yours:** Your on-screen confirmation card system is safer than a static env flag. |
| **Weather Skill** | Live weather forecasts and temperatures | Exa/Serper MCP query | External search API key | `weather_skill.py` (Open-Meteo, free) | **DUPLICATE** | **Keep Yours:** Free, no key required, highly reliable. |
| **News & Briefing Skill** | Live news headlines and daily briefing | Exa/Serper MCP query | External search API key | `news_skill.py`, `briefing_skill.py` | **DUPLICATE** | **Keep Yours:** Existing RSS/API skills are fast and free. |
| **Music Playback Skill** | Audio playback and background ambiance | `public/audio/*.mp3` | Local files | `music_skill.py` (yt-dlp, system audio) | **DUPLICATE** | **Keep Yours:** Can search and play any YouTube track locally. |
| **Notes & Todos Skill** | Note creation and task management | Claude Code filesystem edit | None | `notes_todo_skill.py`, `notes_access.py` | **DUPLICATE** | **Keep Yours:** Persistent local SQLite storage. |
| **System Control & Stats** | Power mode, volume, app launch, process load | Bash MCP server / writes | OS permissions | `system_control_skill.py`, `system_status_skill.py` | **DUPLICATE** | **Keep Yours:** Native macOS/Windows/Linux execution. |

---

## 4. Comprehensive Security Review of Reference Code

Before reusing any code or concepts from `adewaskar/jarvis`, an audit was conducted across seven risk vectors:

### 4.1. Hardcoded Secrets & API Keys
- **Finding:** **CLEAN.**
- **Details:** No hardcoded API keys, private tokens, passwords, or cloud credentials exist anywhere in the code.
- **Reference Evidence:**
  - `bridge/server.mjs:449` and `scripts/setup.mjs:80` dynamically read `process.env.ELEVENLABS_API_KEY` or inspect `~/.claude.json` under the user's home directory.
  - `src/config.ts:132-133` reads `VITE_ANTHROPIC_API_KEY` and `VITE_ELEVENLABS_API_KEY` from Vite env variables.
  - The voice ID `JBFqnCBsd6RMkjVDRZzb` (`bridge/server.mjs:460`) is ElevenLabs' public default voice identifier ("George"), not a private credential.

### 4.2. Telemetry and Unauthorized Third-Party Data Transmission
- **Finding:** **CLEAN with 3 standard upstream services.**
- **Details:**
  1. **Anthropic API:** Used only when running the Claude Agent SDK or in direct mode (`api.anthropic.com`).
  2. **ElevenLabs API:** Audio bytes streamed to `api.elevenlabs.io/v1/text-to-speech` and `api.elevenlabs.io/v1/speech-to-text` only when an ElevenLabs key is configured.
  3. **Google Storage / Hugging Face:**
     - Hand tracking weights downloaded from `https://storage.googleapis.com/mediapipe-models/...`
     - Kokoro TTS model downloaded from `onnx-community/Kokoro-82M-v1.0-ONNX` via Hugging Face.
  4. **No analytics, no error tracking (e.g. Sentry/PostHog), no phone-home telemetry.**

### 4.3. Obfuscation, eval(), exec(), and Dynamic Code Execution
- **Finding:** **NO MALICIOUS OBFUSCATION.**
- **Details:**
  - Code is 100% human-readable TypeScript and ECMAScript modules with extensive inline rationale comments.
  - No `eval()` or `Function()` constructor usage exists in application logic.
  - The string `exec` occurs strictly as `RegExp.prototype.exec()` for regex pattern matching (`net.mjs:64`, `tts.ts:670`, `page.mjs:129`, etc.) and `process.execPath` in `scripts/start.mjs:120`.
  - The CSP in `index.html:56` includes `'unsafe-eval' 'wasm-unsafe-eval'` solely to support ONNX WebAssembly compilation (`kokoro-js`) and espeak-ng phonetic compilation.

### 4.4. Shell & Subprocess Execution with User Input
- **Finding:** **SECURE in Reference Repository; Requires Strict Safeguards in Migration.**
- **Details:**
  - `scripts/setup.mjs:41` uses `spawnSync('claude', ['--version'])` with `shell: false`.
  - `scripts/start.mjs:60-65` uses `spawn(command, args, { shell: false })` to launch `node bridge/server.mjs` and `vite`.
  - The bridge relies on the Claude Agent SDK for executing shell commands via the `Bash` tool. In the reference bridge, effectful shell commands are blocked by default (`decideTool()` blocks `Bash`, `Write`, `Edit`, `MultiEdit` unless `JARVIS_ALLOW_WRITES=1`).
  - **Migration Note:** Your JARVIS already has `actions.py` with an `ALLOWED_COMMANDS` whitelist and confirmation card gating. Do not adopt unvetted bash execution.

### 4.5. Network Listeners, Ports, and Cross-Origin Protections
- **Finding:** **SOLID LOCAL DEFENSE.**
- **Details:**
  - The bridge opens a local HTTP server and WebSocket server on `PORT 8787` (`ws://localhost:8787`).
  - Handshake Origin Guard (`bridge/server.mjs:77-90`): Validates `Origin` header against Vite development ports (5173-5199, 4173-4199) and localhost. Requests from external web origins are rejected with HTTP 403 Forbidden.
  - Non-browser requests (missing Origin) are denied by default unless `JARVIS_ALLOW_NO_ORIGIN=1`.
  - **Vulnerability Gap in Reference Code:** The reference bridge does not use a bearer authentication token; it relies solely on the `Origin` header. Any local process or browser extension on localhost could potentially connect. **Your existing JARVIS uses `JARVIS_AUTH_TOKEN` in WebSocket subprotocols (`bearer.<token>`). When merging endpoints into your JARVIS, enforce your token on all HTTP and WebSocket connections!**

### 4.6. SSRF (Server-Side Request Forgery) & Path Traversal Protections
- **Finding:** **EXEMPLARY DEFENSE-IN-DEPTH.**
- **Details in `bridge/net.mjs` & `bridge/server.mjs`:**
  - **SSRF Blocklist (`blockedAddress` in `net.mjs:55-105`):** Strictly blocks IPv4 link-local & cloud metadata (`169.254.169.254`), loopback (`127.0.0.0/8`, `::1`), zero network (`0.0.0.0/8`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), CGNAT/tailnets (`100.64.0.0/10`), benchmarking range (`198.18.0.0/15`), multicast (`224.0.0.0/4`), IPv6 unique local (`fc00::/7`), and IPv4-mapped IPv6 addresses (`::ffff:127.0.0.1`).
  - **DNS Rebinding Prevention (`guardedLookup` in `net.mjs:117-136`):** Outbound Node HTTP/HTTPS requests resolve DNS via a custom hook that checks all resolved addresses before the socket connects, preventing DNS rebinding TOCTOU attacks.
  - **Manual Redirect Validation (`openRemote` in `net.mjs:216-238`):** Restricts redirect chains to 4 hops and re-evaluates `vetTarget()` and `guardedLookup` on every HTTP 3xx `Location` header to prevent redirects to internal infrastructure.
  - **Path Traversal Guard (`withinRoots` in `server.mjs:482-506`):** For `/file?path=...`, paths are canonicalized via `realpathSync()`. Files are only served if they sit inside allowed roots (`homedir()`, system temp), have permitted image extensions (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`), and strictly exclude scriptable formats like `.svg`.

### 4.7. Supply Chain & Dependency Health
- **Finding:** **SAFE.**
- **Dependencies Audited:**
  - `@anthropic-ai/claude-agent-sdk`, `@anthropic-ai/sdk`: Official Anthropic libraries.
  - `dompurify`: Industry-standard HTML sanitization library.
  - `kokoro-js`: Open-source ONNX WebGPU runtime for Kokoro-82M.
  - `@mediapipe/tasks-vision`: Google's official MediaPipe WebAssembly machine learning library.
  - `three`, `@react-three/fiber`, `@react-three/drei`: Standard 3D WebGL rendering ecosystem.
  - `zod`, `zustand`, `framer-motion`: Standard UI state and validation utilities.
- No malicious or typosquatted packages detected.

---

## 5. Security & Architectural Rules for Phase 2 Merge

To ensure zero regressions and maintain system integrity, Phase 2 implementation must obey these strict rules:

1. **Architecture Preservation:**
   - Implement all new capabilities as modular Python skills in `jarvis/skills/*_skill.py`.
   - Never replace the core FastAPI `server.py` or `ai_brain.py` main event loops.
   - Keep your existing login token, WebSocket subprotocol authorization (`bearer.<token>`), and rate limiting.
2. **Barge-In Safety Guard:**
   - Voice activity detected during barge-in immediately silences TTS speech output.
   - **CRITICAL:** Speech captured during or immediately following barge-in MUST NEVER automatically confirm or trigger restricted skills (such as terminal commands, file deletions, code rewrites, or payments). All restricted actions continue to require explicit on-screen button confirmation cards.
3. **SSRF Guarded Endpoints in Python:**
   - Port `bridge/net.mjs` SSRF validation logic into Python (`httpx` transport with custom DNS resolver and IP blocklist) for proxying `/img` and `/media`.
   - Require `JARVIS_AUTH_TOKEN` verification on proxy requests.
4. **AI-Authored HUD Panels Sanitization:**
   - Frontend panel rendering must pass through DOMPurify with the class allowlist (`ALLOWED_CLASSES`) and SVG/style stripping.
   - Restrict `<iframe>` rendering to YouTube no-cookie (`www.youtube-nocookie.com/embed`) and Vimeo (`player.vimeo.com/video`).
5. **No Rights-Infringing Audio Files:**
   - Do not copy copyrighted Marvel/Iron Man movie boot audio. Use procedural Web Audio API synthesizers (`src/lib/sfx.ts`) and custom royalty-free sounds.

---

## 6. Action Plan for Prompt Execution

When Phase 2 begins, the prompts will be executed in this order:

- **Prompt 1: Voice-controlled interface & AI panels**
  - Implement skills: `ui_theme`, `ui_reactor`, `ui_orbit`, `ui_chrome`, `ui_effect`, `ui_screen`, `ui_reset` in `skills/`.
  - Add Three.js GLSL arc reactor customizations and orbiting textures to `frontend/src/orb.ts`.
  - Implement `/img` and `/media` SSRF-guarded proxy endpoints in `server.py`.
  - Add DOMPurify sanitization with class allowlist in frontend.
  - Update `/skills` HUD panel manifest.

- **Prompt 2: Voice upgrades & diagnostics**
  - Implement client-side VAD barge-in with speech cancellation in `frontend/src/voice.ts`.
  - Add Kokoro WebGPU neural TTS and ElevenLabs streaming fallback.
  - Add `/health` endpoint to `server.py` for capability detection.
  - Add keyboard shortcuts (`Space` PTT, `Esc` Stand down, `V` Voice cycle, `D` Diagnostics panel, `T` Audio test).
  - Create standalone diagnostic check script `setup_check.py`.
  - Implement 4-beat SVG startup sequence with Web Audio sound effects.

- **Prompt 3: Tools (web search, images, browser)**
  - Implement DuckDuckGo / Exa search skill with source card citations.
  - Implement image generation skill with HUD display and orbit option.
  - Implement safe read-only Playwright browser inspection skill with strict confirmation cards for form filling/clicks.
  - Add prompt injection defense: mark external web data as untrusted text that cannot directly trigger skills.
  - Log skill executions cleanly to `logs/ai_skills.log`.
