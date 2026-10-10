// jarvis_website_ws_client.js
// ══════════════════════════════════════════════════════════════════════
// Drop this into your JARVIS frontend swarm pipeline component.
// Replaces the broken REST polling with a real-time WebSocket
// that drives your "Autonomous Command Stream" + progress bars.
// ══════════════════════════════════════════════════════════════════════

class JarvisWebsiteBuilder {
  constructor(wsUrl = "ws://localhost:8000/api/website/ws/generate") {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.onProgress = null;  // callback(progress:int, message:str, file:str)
    this.onFileWritten = null; // callback(filename:str)
    this.onComplete = null;  // callback(result:object)
    this.onError = null;     // callback(message:str)
  }

  build(request) {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        console.log("[JARVIS] WebSocket connected — starting build");
        this.ws.send(JSON.stringify(request));
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "result") {
          this.onComplete && this.onComplete(data);
          this.ws.close();
          resolve(data);
          return;
        }

        if (data.type === "error") {
          this.onError && this.onError(data.message);
          this.ws.close();
          reject(new Error(data.message));
          return;
        }

        // Progress update
        this.onProgress && this.onProgress(data.progress, data.message, data.file);

        if (data.step === "done" && data.file) {
          this.onFileWritten && this.onFileWritten(data.file);
        }
      };

      this.ws.onerror = (err) => {
        console.error("[JARVIS] WebSocket error:", err);
        this.onError && this.onError("WebSocket connection failed");
        reject(err);
      };

      this.ws.onclose = () => {
        console.log("[JARVIS] WebSocket closed");
      };
    });
  }

  cancel() {
    if (this.ws) this.ws.close();
  }
}


// ── USAGE IN YOUR SWARM PIPELINE COMPONENT ─────────────────────────────

async function buildWebsiteWithJARVIS(userRequest) {
  const builder = new JarvisWebsiteBuilder();

  // Wire up to your existing swarm UI elements
  builder.onProgress = (progress, message, file) => {
    // Update your "Autonomous Command Stream" terminal
    appendToCommandStream(`[ STARK COMPILER ] ${message}`);
    // Update your progress bar
    updateProgressBar(progress);
    // Update "File Operations Feed"
    if (file) updateFilesFeed(file, "GENERATING");
  };

  builder.onFileWritten = (filename) => {
    appendToCommandStream(`[ STARK COMPILER ] ✓ ${filename} written`);
    updateFilesFeed(filename, "SUCCESS");
  };

  builder.onComplete = (result) => {
    appendToCommandStream(`[ STARK COMPILER ] ✓ Build complete! ${result.files.length} files generated`);
    appendToCommandStream(`[ STARK COMPILER ] ✓ ZIP ready: ${result.zip}`);
    updateProgressBar(100);
    // Trigger ZIP download
    window.location.href = `/api/website/download/${result.zip.split('/').pop().replace('.zip','')}`;
  };

  builder.onError = (msg) => {
    appendToCommandStream(`[ STARK COMPILER ] ✗ ERROR: ${msg}`);
  };

  try {
    await builder.build({
      name: userRequest.name,
      description: userRequest.description,
      theme: userRequest.theme,
      pages: userRequest.pages,
      stack: userRequest.stack || "html",
      currency: "INR"
    });
  } catch (err) {
    console.error("[JARVIS] Build failed:", err);
  }
}


// ── HELPER: append to your existing command stream terminal ────────────
function appendToCommandStream(text) {
  const stream = document.getElementById("command-stream");
  if (!stream) return;
  const line = document.createElement("div");
  line.textContent = text;
  line.style.color = text.includes("✓") ? "#22c55e" :
                     text.includes("✗") ? "#ef4444" :
                     text.includes("WARNING") ? "#f59e0b" : "#00d4ff";
  stream.appendChild(line);
  stream.scrollTop = stream.scrollHeight;
}

function updateProgressBar(pct) {
  const bar = document.getElementById("progress-bar");
  const label = document.getElementById("progress-label");
  if (bar) bar.style.width = pct + "%";
  if (label) label.textContent = pct + "%";
}

function updateFilesFeed(filename, status) {
  const feed = document.getElementById("files-feed");
  if (!feed) return;
  const row = document.createElement("div");
  row.style.cssText = "display:flex;justify-content:space-between;font-size:12px;padding:3px 0";
  row.innerHTML = `<span style="color:#888">[WRITE]</span>
                   <span style="flex:1;margin:0 8px">${filename}</span>
                   <span style="color:${status==='SUCCESS'?'#22c55e':'#00d4ff'}">${status}</span>`;
  feed.appendChild(row);
}


export { JarvisWebsiteBuilder, buildWebsiteWithJARVIS };
