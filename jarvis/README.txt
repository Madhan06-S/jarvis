# JARVIS Website Builder — Fix Guide
All 4 errors fixed. Follow these 4 steps in order.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 1 — Fix .env (5 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Open: https://console.anthropic.com/settings/keys
2. Create new key → copy it (starts with sk-ant-)
3. Open the .env file in this folder
4. Replace: ANTHROPIC_API_KEY=sk-ant-PASTE_YOUR_REAL_KEY_HERE
   With:     ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx...

5. Optional for real images:
   Open: https://unsplash.com/developers → New Application
   Replace: UNSPLASH_ACCESS_KEY=PASTE_YOUR_UNSPLASH_KEY_HERE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 2 — Drop in the new backend file (30 seconds)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Copy jarvis_website_tool.py → your backend/ folder
(Replace the existing one if present)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 3 — Register the router in main.py (2 lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Open main_patch.py and copy the 2 lines into your backend/main.py:

  from jarvis_website_tool import router as website_router
  app.include_router(website_router, prefix="/api/website")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 4 — Connect real-time WebSocket to your swarm UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Copy jarvis_website_ws_client.js → your frontend/src/ folder
Import and call buildWebsiteWithJARVIS(request) from your
swarm pipeline component. It connects to:
  ws://localhost:8000/api/website/ws/generate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 WHAT EACH FILE FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.env                        → FIX 1: Anthropic key + FIX 2: rate limit config
jarvis_website_tool.py      → FIX 2: backoff + FIX 3: images + FIX 4: self-contained HTML
main_patch.py               → router registration (2 lines)
jarvis_website_ws_client.js → real-time multi-user WebSocket for swarm UI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TEST IT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
curl -X POST http://localhost:8000/api/website/generate-website \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ShopZone",
    "description": "Indian e-commerce store for electronics",
    "theme": "dark neon cyan like JARVIS",
    "pages": ["Home", "Products", "Login", "Checkout"],
    "stack": "html",
    "currency": "INR"
  }'

Expected response:
{
  "status": "ok",
  "files": ["index.html", "products.html", "login.html", "checkout.html"],
  "zip": "./jarvis_projects/ShopZone.zip",
  ...
}
