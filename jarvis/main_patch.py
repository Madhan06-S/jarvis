"""
backend/main.py — patch to add website builder router
Add these lines to your existing main.py
"""

# ── ADD THIS IMPORT at the top of your main.py ───────────────────────────
from jarvis_website_tool import router as website_router

# ── ADD THIS after app = FastAPI(...) ────────────────────────────────────
app.include_router(website_router, prefix="/api/website", tags=["Website Builder"])


# ══════════════════════════════════════════════════════════════════════════
# HOW TO CALL FROM YOUR SWARM PIPELINE
# ══════════════════════════════════════════════════════════════════════════

"""
1. REST API (standard):
   POST http://localhost:8000/api/website/generate-website
   Body:
   {
     "name": "ShopZone",
     "description": "Indian e-commerce store selling electronics and gadgets",
     "theme": "dark with neon cyan accents like JARVIS",
     "pages": ["Home", "Products", "Login", "Checkout"],
     "stack": "html",
     "currency": "INR"
   }

2. WebSocket (real-time progress in swarm UI):
   ws://localhost:8000/api/website/ws/generate
   Send same JSON body → receive live progress events:
   {"step":"generating","progress":45,"message":"Writing Products page...","file":"products.html"}
   {"step":"complete","progress":100,"message":"Website ready!","file":"./jarvis_projects/ShopZone.zip"}

3. Download ZIP after generation:
   GET http://localhost:8000/api/website/download/ShopZone
"""

# ══════════════════════════════════════════════════════════════════════════
# CONNECT WEBSOCKET FROM YOUR JARVIS SWARM FRONTEND (JavaScript)
# ══════════════════════════════════════════════════════════════════════════
FRONTEND_WS_EXAMPLE = """
// In your JARVIS swarm pipeline frontend (React/JS):
const ws = new WebSocket("ws://localhost:8000/api/website/ws/generate");

ws.onopen = () => {
  ws.send(JSON.stringify({
    name: "ShopZone",
    description: "Indian e-commerce for electronics",
    theme: "dark neon cyan JARVIS style",
    pages: ["Home", "Products", "Login", "Checkout"],
    stack: "html",
    currency: "INR"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Update your swarm UI progress bar
  updateAgentProgress(data.progress, data.message, data.file);
  
  if (data.type === "result") {
    // Generation complete — trigger download
    window.location.href = `/api/website/download/${data.zip.split('/').pop().replace('.zip','')}`;
  }
  if (data.type === "error") {
    console.error("JARVIS build error:", data.message);
  }
};
"""
