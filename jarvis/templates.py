"""
ANTIGRAVITY JARVIS — Elite 3D Scaffold Generator
Stack: React 18 + Vite + Three.js + GSAP + Framer Motion + Tailwind CSS + FastAPI
"""
from fallback_education import get_fallback_app


import re

def classify_domain(description: str, title: str) -> str:
    text = (description + " " + title).lower()
    words = set(re.findall(r'\b\w+\b', text))
    
    if any(w in words for w in ["food","delivery","restaurant","order","meal","eat","menu","burger","pizza"]):
        return "food_delivery"
    if any(w in words for w in ["hospital","doctor","patient","medical","clinic","health","appointment","pharma"]):
        return "hospital"
    if any(w in words for w in ["ecommerce","shop","store","product","cart","buy","sell","marketplace","supermarket"]):
        return "ecommerce"
    if any(w in words for w in ["portfolio","resume","personal","developer","designer","showcase","cv"]):
        return "portfolio"
    if any(w in words for w in ["saas","dashboard","analytics","crm","billing","subscription","enterprise"]):
        return "saas"
    if any(w in words for w in ["gym","fitness","workout","trainer","exercise"]):
        return "fitness"
    if any(w in words for w in ["hotel","booking","travel","airbnb","accommodation","resort"]):
        return "travel"
    if any(w in words for w in ["blog","news","article","post","content","media"]):
        return "blog"
    if any(w in words for w in ["school","education","course","learning","student","teacher","lms"]):
        return "education"
    
    # Check for substring matches as a fallback only if no direct word match was found
    if "e-commerce" in text: return "ecommerce"
    
    return "generic"


def get_domain_prompt(domain: str, plan: dict, description: str,
                       images: dict = None) -> str:
    title  = plan.get("title", "My App")
    db     = plan.get("db",    "sqlite")
    theme  = plan.get("theme", "modern dark")
    images = images or {}

    img_block = ""
    if images:
        img_lines = "\n".join(f'  {k}: "{v}"' for k, v in images.items())
        img_block = f"""
REAL AI-GENERATED IMAGE URLS (use these directly in <img src=...> or CSS background-image):
{img_lines}
Replace ALL placeholder images with these real URLs.
"""

    pages = {
        "food_delivery": [
            "Landing page with 3D animated hero banner, floating food items, restaurant list below",
            "Restaurant listing grid with search/filter, animated cards on hover, REAL API calls to /api/restaurants",
            "Restaurant detail page with menu items from /api/menu?restaurant_id=X, add-to-cart with spring animation",
            "Shopping cart sidebar with GSAP slide-in, quantity controls, subtotal, REAL cart state management",
            "Checkout page with address form, payment UI, animated order summary, POST to /api/orders",
            "Order tracking page with animated progress steps, estimated time, GET from /api/orders/:id",
            "Admin panel with data table, order management, status updates, REAL CRUD operations",
        ],
        "hospital": [
            "Landing page with 3D hero, animated stats counter, doctor cards from /api/doctors, services",
            "Doctor directory with specialty filter, animated profile cards, REAL API calls to /api/doctors",
            "Appointment booking with date picker, doctor select, patient info form, POST to /api/appointments",
            "Patient dashboard with upcoming appointments from /api/patient/:id/appointments, medical history timeline",
            "Medical records page with downloadable docs list, GET from /api/patient/:id/records",
            "Billing page with invoice list, payment status badges, GET from /api/patient/:id/billing",
            "Admin dashboard with patient stats, appointment calendar, REAL CRUD operations",
        ],
        "ecommerce": [
            "Landing page with 3D product hero, rotating featured products from /api/products/featured, categories",
            "Product listing grid with animated filter sidebar, hover effects, REAL API calls to /api/products",
            "Product detail page with 3D-style image gallery, add to cart animation, GET from /api/products/:id",
            "Shopping cart with quantity controls, coupon code, animated price, REAL cart state management",
            "Checkout with shipping form, payment method, order summary, POST to /api/orders",
            "Order history page with status tracking timeline, GET from /api/customer/:id/orders",
            "Admin inventory with product CRUD table, chart stats, REAL product management",
        ],
        "portfolio": [
            "Hero section with Three.js 3D particle background, name, animated tagline",
            "About section with bio, animated skills bars, floating tech badges",
            "Projects grid with 3D tilt cards, tech stack tags, live/github links",
            "Skills section with animated tech icons, 3D category spheres",
            "Experience timeline with scroll-triggered GSAP animations",
            "Contact section with animated form, social links, floating icons",
        ],
        "saas": [
            "Marketing landing with 3D hero, animated features, pricing table from /api/plans, testimonials",
            "Login and Register pages with glassmorphism cards, smooth transitions, POST to /api/auth/login/register",
            "Main dashboard with animated KPI stat cards from /api/dashboard/stats, Chart.js charts, activity feed",
            "Analytics page with line charts, bar graphs, data tables, GET from /api/analytics",
            "Settings page with profile edit, notification toggles, PUT to /api/user/profile",
            "Billing page with plan comparison, invoice history from /api/billing/invoices, upgrade CTA",
            "Team management with member list from /api/team/members, invite form, role badges, REAL team CRUD",
        ],
        "fitness": [
            "Landing with full-screen 3D hero, class schedule from /api/classes/schedule, animated trainer cards from /api/trainers",
            "Workout plans page with category cards, difficulty filter, 3D flip cards, GET from /api/workouts",
            "Individual workout detail with exercise list from /api/workouts/:id/exercises, animated timers",
            "Membership pricing with animated plan comparison table, GET from /api/membership/plans",
            "Member dashboard with progress charts from /api/member/:id/progress, streak calendar",
            "Book a class with schedule grid, animated booking confirmation, POST to /api/bookings",
        ],
        "travel": [
            "Landing with parallax 3D hero, destination search, animated featured cards from /api/destinations/featured",
            "Hotel listing grid with filter by price/rating/amenities, REAL API calls to /api/hotels",
            "Property detail with image gallery, amenities icons, map embed, reviews, GET from /api/hotels/:id",
            "Booking form with date picker, guest selector, animated price summary, POST to /api/bookings",
            "My bookings page with reservation list and status timeline, GET from /api/user/:id/bookings",
            "Explore destinations with animated city cards, hover 3D lift effect, GET from /api/destinations",
        ],
        "blog": [
            "Home with featured post hero from /api/posts/featured, 3D animated header, recent posts grid from /api/posts",
            "Blog listing with category filter, search, paginated post cards, REAL API calls to /api/posts",
            "Individual post with full content from /api/posts/:id, author bio, animated comments, POST to /api/posts/:id/comments",
            "Category pages with filtered posts from /api/posts?category=X, tag cloud",
            "Author profile with avatar, bio, post list from /api/authors/:id/posts",
            "Admin editor with rich text, publish controls, SEO preview, POST to /api/posts",
        ],
        "education": [
            "Landing with 3D animated hero, course categories from /api/courses/categories, stats, testimonials",
            "Course catalog with filter by subject/level/price, animated cards, REAL API calls to /api/courses",
            "Course detail with curriculum accordion from /api/courses/:id/curriculum, instructor card, enroll CTA, POST to /api/enrollments",
            "Student dashboard with enrolled courses from /api/student/:id/courses, animated progress bars",
            "Lesson viewer with video player, chapter sidebar, notes, GET from /api/lessons/:id",
            "Quiz page with animated question cards from /api/quizzes/:id/questions, timer, results screen, POST to /api/quizzes/:id/submit",
            "Instructor admin with course CRUD, student analytics charts, REAL course management",
        ],
        "generic": [
            "Landing with 3D animated hero section, feature grid, testimonials, CTA",
            "Dashboard with animated KPI stat cards from /api/dashboard/stats and recent activity",
            "List/management page with search, filter, CRUD data table, REAL API calls to /api/items",
            "Detail/edit page with animated form for individual records, GET/PUT to /api/items/:id",
            "Settings page with toggle switches and preferences, PUT to /api/user/settings",
            "Login and register pages with glassmorphism forms, POST to /api/auth/login/register",
        ],
    }

    page_list = pages.get(domain, pages["generic"])
    page_str  = "\n".join(f"  - {p}" for p in page_list)

    color_palettes = {
        "food_delivery": "Warm: #FF6B35 (primary), #FF8C42 (accent), #1A0A00 (dark bg), #2D1A0E (card)",
        "hospital":      "Medical: #00B4D8 (primary), #90E0EF (accent), #03045E (dark bg)",
        "ecommerce":     "Premium: #6C63FF (primary), #A78BFA (accent), #0F0F1A (dark bg)",
        "portfolio":     "Dev: #8B5CF6 (primary), #A78BFA (accent), #050505 (dark bg), cyan highlights",
        "saas":          "Pro: #6366F1 (primary), #818CF8 (accent), #0F172A (dark bg), slate cards",
        "fitness":       "Energy: #F59E0B (primary), #EF4444 (accent), #0A0A0A (dark bg), neon glow",
        "travel":        "Ocean: #0EA5E9 (primary), #F59E0B (accent), #042330 (dark bg)",
        "blog":          "Content: #EC4899 (primary), #F472B6 (accent), #0F0617 (dark bg)",
        "education":     "Learn: #10B981 (primary), #34D399 (accent), #022C22 (dark bg)",
        "generic":       "Modern: #6366F1 (primary), #8B5CF6 (accent), #0F172A (dark bg)",
    }
    palette = color_palettes.get(domain, color_palettes["generic"])

    return f"""You are not a beginner web generator anymore.

You are JARVIS — an elite AI full-stack architect inspired by Iron Man technology.

Whenever I give a website idea, you must first deeply analyze:
- brand identity
- user psychology
- modern UI/UX trends
- animations
- futuristic interactions
- premium SaaS design patterns
- 3D visuals
- color psychology
- responsiveness
- conversion optimization
- cinematic experience

Then generate a COMPLETE high-end production-ready website automatically.

BUILD TARGET: {title}
DOMAIN: {domain.replace("_", " ").upper()}
DESCRIPTION: {description}
DATABASE: {db}
THEME: {theme}
COLOR PALETTE: {palette}
{img_block}

IMPORTANT RULES:
1. NEVER generate simple/basic layouts.
2. NEVER create plain bootstrap-like pages.
3. NEVER use boring cards and simple buttons only.
4. Every website must feel like a premium Apple + Tesla + Iron Man level product.
5. Every page should look award-winning like Awwwards websites.

DESIGN STYLE:
- Futuristic UI, Glassmorphism, Smooth gradients, Dark premium themes
- Floating animations, Neon glows, 3D depth, Scroll animations
- Micro interactions, Motion effects, Cinematic transitions
- Interactive hover effects, Animated backgrounds, Particle systems, Cursor effects, AI futuristic aesthetics

TECH STACK:
Frontend: React 18 + TypeScript + TailwindCSS + Framer Motion + Three.js / React Three Fiber + GSAP + Lenis smooth scroll + ShadCN UI + Lucide React
Backend: Node.js / Express (or FastAPI + SQLAlchemy if specified)
DB: MongoDB, Supabase, or SQLite/PostgreSQL
Auth: JWT auth
API: REST APIs

AI BEHAVIOR:
Before generating code:
1. Analyze the project deeply
2. Decide best layout automatically
3. Decide best color palette automatically ({palette})
4. Decide animation style automatically
5. Decide sections automatically
6. Generate modern copywriting automatically
7. Create realistic premium UI structure

OUTPUT REQUIREMENTS:
- Fully responsive & Mobile optimized
- Premium navbar & Hero section with 3D visuals
- Scroll animations & Interactive sections
- Testimonials, Pricing, FAQ if needed & Footer
- Advanced loading screen & Smooth page transitions
- Fully animated components & Production-ready folder structure

FOR EVERY WEBSITE:
Create:
- Landing page, About page, Dashboard if relevant, Contact page, Authentication pages
- Reusable components, Animations folder, API structure, Modern assets placeholders

SPECIAL MODE:
Whenever possible:
- Use 3D models & Add floating holographic effects
- Add AI assistant style interactions & Add voice/command UI inspiration
- Add futuristic HUD interfaces & Add cinematic scrolling experience

QUALITY STANDARD:
The result should look like: Marvel movie UI, Iron Man HUD, Tesla website, Apple keynote animations, Premium SaaS startup, Awwwards winner

DO NOT SIMPLIFY ANYTHING.
Think for longer before generating.
Act like a $1M UI/UX agency with elite engineers.
Generate complete code with proper architecture and stunning visuals.

━━━ PAGES TO BUILD (ALL in one App.tsx using React state navigation) ━━━
{page_str}

━━━ OUTPUT FORMAT — output ONLY these exact blocks ━━━

```tsx filename="frontend/src/App.tsx"
// COMPLETE React app with ALL pages, Three.js 3D, Framer Motion, GSAP
```

```css filename="frontend/src/index.css"
/* Complete CSS with custom animations, glassmorphism utilities */
```

```python filename="backend/main.py"
# Complete FastAPI backend with REAL domain-specific routes
```
"""


def get_react_fastapi_files(plan: dict, description: str = "") -> dict:
    title  = plan.get("title", "My App")
    domain = classify_domain(description or plan.get("description", ""), title)

    return {
        # ── Frontend package.json with THREE.JS + GSAP + FRAMER MOTION ──
        "frontend/package.json": """{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@react-three/fiber": "^8.17.10",
    "@react-three/drei": "^9.109.2",
    "three": "^0.168.0",
    "framer-motion": "^11.3.30",
    "gsap": "^3.12.5",
    "@gsap/react": "^2.1.1",
    "lucide-react": "^0.412.0",
    "axios": "^1.7.2",
    "recharts": "^2.12.7",
    "react-hot-toast": "^2.4.1",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/three": "^0.168.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.2.2",
    "vite": "^5.3.4"
  }
}""",

        # ── Vite config with proxy ──
        "frontend/vite.config.ts": """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
""",
        # ── Tailwind config with custom animations ──
        "frontend/tailwind.config.ts": """/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Syne', 'Inter', 'sans-serif'],
      },
      animation: {
        'fade-in':     'fadeIn 0.6s ease-out both',
        'slide-up':    'slideUp 0.5s ease-out both',
        'slide-right': 'slideRight 0.5s ease-out both',
        'float':       'float 6s ease-in-out infinite',
        'glow':        'glow 2s ease-in-out infinite',
        'spin-slow':   'spin 8s linear infinite',
        'pulse-slow':  'pulse 4s ease-in-out infinite',
        'gradient':    'gradient 8s ease infinite',
        'count-up':    'countUp 1s ease-out both',
      },
      keyframes: {
        fadeIn:    { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp:   { from: { transform: 'translateY(30px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        slideRight:{ from: { transform: 'translateX(-30px)', opacity: '0' }, to: { transform: 'translateX(0)', opacity: '1' } },
        float:     { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-20px)' } },
        glow:      { '0%,100%': { boxShadow: '0 0 20px rgba(99,102,241,0.4)' }, '50%': { boxShadow: '0 0 40px rgba(99,102,241,0.8)' } },
        gradient:  { '0%,100%': { backgroundPosition: '0% 50%' }, '50%': { backgroundPosition: '100% 50%' } },
        countUp:   { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
      backgroundSize: { '200%': '200%' },
    },
  },
  plugins: [],
}""",

        "frontend/postcss.config.js": """export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
""",
        "frontend/index.html": f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <meta name="description" content="{title} — Built by ANTIGRAVITY JARVIS" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",
        "frontend/src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""",
        # Loading stub — AI overwrites this
        "frontend/src/App.tsx": """import React from 'react';
import { motion } from 'framer-motion';
export default function App() {
  return (
    <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%)',color:'#fff',fontFamily:'Inter,sans-serif'}}>
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.16,1,0.3,1] }}
        style={{ textAlign:'center' }}
      >
        <div style={{width:80,height:80,borderRadius:'50%',border:'3px solid transparent',backgroundImage:'linear-gradient(#0f172a,#0f172a),linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899)',backgroundOrigin:'border-box',backgroundClip:'padding-box,border-box',animation:'spin 1.2s linear infinite',margin:'0 auto 24px'}}/>
        <h1 style={{fontSize:28,fontWeight:700,background:'linear-gradient(135deg,#6366f1,#8b5cf6)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',marginBottom:8}}>ANTIGRAVITY JARVIS</h1>
        <p style={{color:'#64748b',fontSize:14,letterSpacing:2}}>GENERATING YOUR 3D APP...</p>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </motion.div>
    </div>
  );
}
""",
        "frontend/src/index.css": """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;

*, *::before, *::after { box-sizing: border-box; margin: 0; }

:root {
  --primary: #6366f1;
  --accent:  #8b5cf6;
  --bg:      #0f172a;
  --card:    rgba(255,255,255,0.04);
  --border:  rgba(255,255,255,0.08);
  --text:    #e2e8f0;
  --muted:   #64748b;
}

html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; overflow-x: hidden; }

/* Glassmorphism */
.glass {
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.08);
}
.glass-strong {
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255,255,255,0.15);
}

/* 3D tilt card */
.tilt-card {
  transform-style: preserve-3d;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.tilt-card:hover {
  transform: perspective(1000px) rotateX(-4deg) rotateY(4deg) translateZ(10px);
  box-shadow: 20px 20px 60px rgba(0,0,0,0.5), -2px -2px 20px rgba(99,102,241,0.15);
}

/* Gradient text */
.gradient-text {
  background: linear-gradient(135deg, var(--primary), var(--accent), #ec4899);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradient 6s ease infinite;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.7); }

/* Magnetic button */
.btn-magnetic {
  position: relative;
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);
}
.btn-magnetic::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--x,50%) var(--y,50%), rgba(255,255,255,0.15), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
}
.btn-magnetic:hover::after { opacity: 1; }

/* Neon glow borders */
.neon-border {
  border: 1px solid rgba(99,102,241,0.3);
  box-shadow: 0 0 20px rgba(99,102,241,0.1), inset 0 0 20px rgba(99,102,241,0.05);
  transition: box-shadow 0.3s, border-color 0.3s;
}
.neon-border:hover {
  border-color: rgba(99,102,241,0.6);
  box-shadow: 0 0 30px rgba(99,102,241,0.3), inset 0 0 30px rgba(99,102,241,0.1);
}

/* Skeleton loading */
.skeleton {
  background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer { to { background-position: -200% 0; } }

/* Noise texture overlay */
.noise::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  pointer-events: none;
}

/* Utility */
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }

/* Page transition */
.page-enter { animation: fadeIn 0.4s ease-out both; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
""",

        # Backend scaffold
        "backend/requirements.txt": """fastapi
uvicorn[standard]
sqlalchemy
aiosqlite
pydantic
python-dotenv
python-multipart
python-jose[cryptography]
passlib[bcrypt]
httpx
Pillow
""",
        "backend/database.py": """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.relationship import relationship
import os
import datetime
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Generic base model
class BaseModel(Base):
    __abstract__ = True
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Domain-specific models will be added by AI based on project type
class Item(BaseModel):
    __tablename__ = "items"
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float)
    available = Column(Boolean, default=True)

# Food delivery models
class Restaurant(BaseModel):
    __tablename__ = "restaurants"
    name = Column(String(200), nullable=False)
    cuisine = Column(String(100))
    rating = Column(Float)
    address = Column(Text)
    image_url = Column(String(500))

class MenuItem(BaseModel):
    __tablename__ = "menu_items"
    restaurant_id = Column(String, ForeignKey("restaurants.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String(100))
    image_url = Column(String(500))
    restaurant = relationship("Restaurant")

class Order(BaseModel):
    __tablename__ = "orders"
    user_id = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default="pending")
    delivery_address = Column(Text)

class OrderItem(BaseModel):
    __tablename__ = "order_items"
    order_id = Column(String, ForeignKey("orders.id"))
    item_id = Column(String, ForeignKey("menu_items.id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

# E-commerce models
class Product(BaseModel):
    __tablename__ = "products"
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String(100))
    image_url = Column(String(500))
    stock = Column(Integer, default=0)

class Customer(BaseModel):
    __tablename__ = "customers"
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(50))
    address = Column(Text)

# User/Authentication models
class User(BaseModel):
    __tablename__ = "users"
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(50), default="user")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
        "backend/main.py": f"""from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, Base, get_db
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="{title} API")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174","http://127.0.0.1:5174","*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Pydantic models
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: str
    class Config:
        from_attributes = True

# Generic CRUD endpoints
@app.get("/api/health")
async def health():
    return {{"status": "OK", "service": "{title}", "version": "1.0.0"}}

@app.get("/api/items", response_model=List[Item])
async def get_items(db: AsyncSession = Depends(get_db)):
    # Generic items endpoint - customize based on domain
    return []

@app.post("/api/items", response_model=Item)
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    # Generic create endpoint - customize based on domain
    new_item = Item(id=str(uuid.uuid4()), **item.dict())
    return new_item

@app.get("/api/items/{{item_id}}", response_model=Item)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    # Generic get endpoint - customize based on domain
    return Item(id=item_id, name="Sample Item", description="Sample description")

@app.put("/api/items/{{item_id}}", response_model=Item)
async def update_item(item_id: str, item: ItemCreate, db: AsyncSession = Depends(get_db)):
    # Generic update endpoint - customize based on domain
    return Item(id=item_id, **item.dict())

@app.delete("/api/items/{{item_id}}")
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db)):
    # Generic delete endpoint - customize based on domain
    return {{"message": "Item deleted successfully"}}
""",
        "_domain": domain,
    }
