import os
import sys
import shutil
import subprocess
from pathlib import Path

# Config
PROJECTS_DIR = Path("C:/Users/nandh/jarvis-projects")
PROJECT_NAME = "nexus-space-tourism"
PROJECT_PATH = PROJECTS_DIR / PROJECT_NAME

print(f"Initializing Force-Scaffold for: {PROJECT_PATH}")
PROJECT_PATH.mkdir(parents=True, exist_ok=True)

# 1. Write frontend/package.json
package_json = """{
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
    "framer-motion": "^11.3.30",
    "gsap": "^3.12.5",
    "lucide-react": "^0.412.0",
    "axios": "^1.7.2",
    "recharts": "^2.12.7",
    "react-hot-toast": "^2.4.1",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.2.2",
    "vite": "^5.3.4"
  }
}"""

# 2. Write frontend/vite.config.ts
vite_config = """import { defineConfig } from 'vite';
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
"""

# 3. Write frontend/tailwind.config.ts
tailwind_config = """/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}"""

# 4. Write frontend/postcss.config.js
postcss_config = """export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}"""

# 5. Write frontend/index.html
index_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>NEXUS Space Tourism — Explore Beyond</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Syne:wght@700;800&display=swap" rel="stylesheet">
  </head>
  <body class="bg-slate-950 text-slate-100 overflow-x-hidden">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

# 6. Write frontend/src/main.tsx
main_tsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

# 7. Write frontend/src/index.css
index_css = """@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #020617;
  color: #f8fafc;
  font-family: 'Inter', sans-serif;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-panel-strong {
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.text-glow {
  text-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
}

.neon-border {
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
}

::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #020617;
}
::-webkit-scrollbar-thumb {
  background: #1e1b4b;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #312e81;
}
"""

# 8. Write frontend/src/App.tsx
app_tsx = """import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Rocket, Globe, Compass, Calendar, Shield, Activity, 
  ChevronRight, Star, User, Cpu, ArrowRight, CheckCircle2,
  X, AlertCircle, RefreshCw
} from 'lucide-react';

const DESTINATIONS = [
  {
    id: "mars",
    name: "Mars Oasis",
    distance: "225M km",
    duration: "9 Months",
    temp: "-62°C",
    desc: "Experience the majestic red canyons, stand atop Olympus Mons, and live in our premium glass domes.",
    price: "$250,000",
    img: "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&q=80"
  },
  {
    id: "europa",
    name: "Europa Ice Caves",
    distance: "628M km",
    duration: "3 Years",
    temp: "-160°C",
    desc: "Sub-glacial submarine excursions beneath the frozen ocean of Jupiter's most famous moon.",
    price: "$750,000",
    img: "https://images.unsplash.com/photo-1614314107768-6018061b5b5d?w=800&q=80"
  },
  {
    id: "titan",
    name: "Titan Methane Seas",
    distance: "1.2B km",
    duration: "7 Years",
    temp: "-179°C",
    desc: "Fly through the dense atmosphere with personal wings and cruise across liquid methane lakes.",
    price: "$1,200,000",
    img: "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=800&q=80"
  }
];

export default function App() {
  const [tab, setTab] = useState('home');
  const [selDest, setSelDest] = useState(DESTINATIONS[0]);
  const [crewCount, setCrewCount] = useState(1);
  const [passType, setPassType] = useState('Explorer');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [bookingSuccess, setBookingSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Simulated telemetry
  const [telemetry, setTelemetry] = useState({
    speed: 42150,
    fuel: 98.4,
    shield: 100,
    oxygen: 99.8
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry(t => ({
        speed: t.speed + Math.floor(Math.random() * 20) - 10,
        fuel: Math.max(80, +(t.fuel - 0.001).toFixed(3)),
        shield: Math.max(95, t.shield + Math.floor(Math.random() * 3) - 1),
        oxygen: +(t.oxygen - 0.0001).toFixed(4)
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email) {
      setError('Please fill in all fields, Cadet.');
      return;
    }
    setError('');
    setLoading(true);
    
    // Attempt real API call, fallback on failure
    try {
      const response = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email,
          destination: selDest.name,
          passengers: crewCount,
          pass_type: passType
        })
      });
      if (response.ok) {
        setBookingSuccess(true);
      } else {
        throw new Error('API failed');
      }
    } catch (err) {
      // Local fallback for offline simulation
      setTimeout(() => {
        setBookingSuccess(true);
      }, 1000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans relative selection:bg-indigo-500/30 overflow-hidden">
      {/* Background Star field */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.08)_0,transparent_60%)] pointer-events-none z-0" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
      
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setTab('home')}>
            <div className="w-10 h-10 bg-indigo-600 flex items-center justify-center rounded-xl rotate-6 shadow-lg shadow-indigo-500/20">
              <Rocket className="w-6 h-6 text-white -rotate-6" />
            </div>
            <span className="text-2xl font-black tracking-tighter text-white uppercase font-display">
              NEXUS<span className="text-indigo-500 text-glow">COSMIC</span>
            </span>
          </div>
          <div className="flex items-center gap-8 font-semibold text-sm">
            {['home', 'destinations', 'book', 'dashboard'].map(t => (
              <button 
                key={t} 
                onClick={() => { setTab(t); setBookingSuccess(false); }} 
                className={`capitalize transition-all hover:text-white ${tab === t ? 'text-indigo-400 text-glow' : 'text-slate-400'}`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-grow pt-20 relative z-10">
        <AnimatePresence mode="wait">
          {tab === 'home' && (
            <motion.div 
              key="home" 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6 py-20"
            >
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                <div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold tracking-widest mb-6 rounded-full">
                    <Star className="w-3 h-3" /> SPACE TOURISM IS HERE
                  </div>
                  <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-[0.9] mb-8 font-display">
                    EXPLORE <br/>
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-500 to-pink-500">
                      BEYOND
                    </span>
                  </h1>
                  <p className="text-lg text-slate-400 mb-10 max-w-xl">
                    NexusCosmic brings you elite commercial voyages to the moons and planets of our solar system. Safe, luxurious, and completely life-changing.
                  </p>
                  <div className="flex gap-4">
                    <button 
                      onClick={() => setTab('destinations')}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-8 py-4 rounded-full flex items-center gap-2 hover:scale-105 transition-all shadow-lg shadow-indigo-600/30"
                    >
                      Browse Destinations <ArrowRight className="w-5 h-5" />
                    </button>
                    <button 
                      onClick={() => setTab('dashboard')}
                      className="bg-white/5 hover:bg-white/10 text-white border border-white/10 font-bold px-8 py-4 rounded-full transition-all"
                    >
                      System Telemetry
                    </button>
                  </div>
                </div>
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/20 to-pink-500/20 rounded-full blur-[80px] z-0 pointer-events-none" />
                  <motion.div 
                    animate={{ y: [0, -15, 0] }}
                    transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                    className="relative z-10 glass-panel p-8 rounded-3xl border border-white/10 shadow-2xl"
                  >
                    <img 
                      src="https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&q=80" 
                      alt="Space Flight"
                      className="w-full h-[400px] object-cover rounded-2xl grayscale hover:grayscale-0 transition-all duration-700"
                    />
                    <div className="mt-6 flex justify-between items-center">
                      <div>
                        <p className="text-xs text-indigo-400 font-bold tracking-widest">ACTIVE LAUNCHER</p>
                        <p className="text-xl font-bold">NEXUS ODYSSEY-9</p>
                      </div>
                      <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold">
                        READY FOR LAUNCH
                      </span>
                    </div>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )}

          {tab === 'destinations' && (
            <motion.div 
              key="dest" 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6 py-20"
            >
              <h2 className="text-4xl font-black tracking-tight mb-12">SELECT YOUR DESTINATION</h2>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {DESTINATIONS.map(d => (
                  <div 
                    key={d.id} 
                    onClick={() => { setSelDest(d); setTab('book'); }}
                    className="glass-panel hover:glass-panel-strong transition-all duration-300 rounded-3xl overflow-hidden cursor-pointer group flex flex-col h-full border border-white/5"
                  >
                    <div className="relative h-60 overflow-hidden">
                      <img 
                        src={d.img} 
                        alt={d.name} 
                        className="w-full h-full object-cover grayscale group-hover:grayscale-0 group-hover:scale-110 transition-all duration-500"
                      />
                      <div className="absolute top-4 right-4 bg-slate-950/80 backdrop-blur px-4 py-1.5 rounded-full border border-white/10 text-sm font-bold text-indigo-400">
                        {d.price}
                      </div>
                    </div>
                    <div className="p-6 flex-grow flex flex-col justify-between">
                      <div>
                        <h3 className="text-2xl font-black mb-3">{d.name}</h3>
                        <p className="text-slate-400 text-sm mb-6 leading-relaxed">{d.desc}</p>
                      </div>
                      <div className="grid grid-cols-3 gap-2 py-4 border-t border-white/5 text-center text-xs">
                        <div>
                          <p className="text-slate-500 font-bold mb-1">DISTANCE</p>
                          <p className="font-semibold text-white">{d.distance}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 font-bold mb-1">DURATION</p>
                          <p className="font-semibold text-white">{d.duration}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 font-bold mb-1">TEMP</p>
                          <p className="font-semibold text-white">{d.temp}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {tab === 'book' && (
            <motion.div 
              key="book" 
              initial={{ opacity: 0, scale: 0.95 }} 
              animate={{ opacity: 1, scale: 1 }} 
              exit={{ opacity: 0 }}
              className="max-w-2xl mx-auto px-6 py-20"
            >
              <div className="glass-panel p-8 md:p-12 rounded-3xl border border-white/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
                
                {bookingSuccess ? (
                  <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="text-center py-12">
                    <CheckCircle2 className="w-20 h-20 text-emerald-500 mx-auto mb-6 shadow-lg shadow-emerald-500/10" />
                    <h3 className="text-3xl font-black mb-4">BOARDING PASS ISSUED</h3>
                    <p className="text-slate-400 mb-8 max-w-md mx-auto">
                      Congratulations, Cadet. Your pass to <span className="text-white font-bold">{selDest.name}</span> has been confirmed. Telemetry details sent to your neural comms.
                    </p>
                    <button 
                      onClick={() => setTab('dashboard')}
                      className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-full hover:bg-indigo-500 transition-colors"
                    >
                      Enter Control Room
                    </button>
                  </motion.div>
                ) : (
                  <form onSubmit={handleBook} className="space-y-6">
                    <div>
                      <h2 className="text-3xl font-black mb-2">SECURE YOUR CABIN</h2>
                      <p className="text-slate-400 text-sm">Voyage destination: <span className="text-indigo-400 font-bold">{selDest.name}</span></p>
                    </div>

                    {error && (
                      <div className="flex items-center gap-2 p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-xl">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span>{error}</span>
                      </div>
                    )}

                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Cadet Name</label>
                      <input 
                        type="text" 
                        value={name}
                        onChange={e => setName(e.target.value)}
                        placeholder="e.g. Neil Armstrong"
                        className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-indigo-500 transition-colors text-white"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sub-Space Email</label>
                      <input 
                        type="email" 
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        placeholder="e.g. neil@nasa.earth"
                        className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-indigo-500 transition-colors text-white"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Crew Size</label>
                        <select 
                          value={crewCount} 
                          onChange={e => setCrewCount(Number(e.target.value))}
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-indigo-500 text-white"
                        >
                          {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} Passenger{n>1?'s':''}</option>)}
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Cabin Class</label>
                        <select 
                          value={passType} 
                          onChange={e => setPassType(e.target.value)}
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-indigo-500 text-white"
                        >
                          {['Explorer', 'Commander', 'Celestial VIP'].map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                    </div>

                    <button 
                      type="submit" 
                      disabled={loading}
                      className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-xl transition-all hover:scale-[1.01] flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
                    >
                      {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : 'CONFIRM EMBARKATION'}
                    </button>
                  </form>
                )}
              </div>
            </motion.div>
          )}

          {tab === 'dashboard' && (
            <motion.div 
              key="dash" 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6 py-20"
            >
              <h2 className="text-4xl font-black tracking-tight mb-12">MISSION CONTROL HUD</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {[
                  { l: "ORBITAL SPEED", v: `${telemetry.speed.toLocaleString()} km/h`, icon: Cpu, c: "text-indigo-400" },
                  { l: "FUEL RESERVE", v: `${telemetry.fuel}%`, icon: Globe, c: "text-emerald-400" },
                  { l: "FORCE FIELD SHIELD", v: `${telemetry.shield}%`, icon: Shield, c: "text-cyan-400" },
                  { l: "CABIN O2 RECYLER", v: `${telemetry.oxygen}%`, icon: Activity, c: "text-pink-400" }
                ].map((s, i) => (
                  <div key={i} className="glass-panel p-6 rounded-3xl border border-white/5 relative overflow-hidden group hover:border-white/10 transition-colors">
                    <div className="flex justify-between items-start mb-6">
                      <p className="text-xs text-slate-500 font-bold">{s.l}</p>
                      <s.icon className={`w-5 h-5 ${s.c}`} />
                    </div>
                    <h3 className="text-2xl font-black tracking-tighter text-white">{s.v}</h3>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 glass-panel p-8 rounded-3xl border border-white/5 min-h-[400px] flex flex-col justify-center items-center text-center">
                  <Cpu className="w-16 h-16 text-indigo-500/40 mb-4 animate-pulse" />
                  <h4 className="text-xl font-bold mb-2">Simulated Warp Trajectory</h4>
                  <p className="text-sm text-slate-500 max-w-sm">
                    Connecting to the local quantum node. Sub-orbital path plotting active.
                  </p>
                </div>
                <div className="glass-panel p-8 rounded-3xl border border-white/5">
                  <h3 className="font-bold text-lg mb-6 text-indigo-400">Crew Manifest Logs</h3>
                  <div className="space-y-6">
                    {[
                      { cadet: "Commander Shepard", status: "Active", time: "2 min ago" },
                      { cadet: "Lt. Starbuck", status: "Ready", time: "12 min ago" },
                      { cadet: "Dr. Brand", status: "Sleeping", time: "42 min ago" }
                    ].map((c, i) => (
                      <div key={i} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                        <div>
                          <p className="text-sm font-semibold text-white">{c.cadet}</p>
                          <p className="text-xs text-slate-500">{c.time}</p>
                        </div>
                        <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-bold rounded">
                          {c.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="py-8 border-t border-white/5 text-center text-xs text-slate-600 relative z-10 bg-slate-950">
        <p>© 2026 NEXUSCOSMIC. All rights reserved. Deployed by ANTIGRAVITY JARVIS.</p>
      </footer>
    </div>
  );
}
"""

# 9. Write backend/requirements.txt
requirements_txt = """fastapi
uvicorn[standard]
sqlalchemy
aiosqlite
pydantic
python-dotenv
python-multipart
httpx
"""

# 10. Write backend/database.py
database_py = """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, DateTime
import os
import datetime
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./space.db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    passengers = Column(Integer, default=1)
    pass_type = Column(String, default="Explorer")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
"""

# 11. Write backend/main.py
main_py = """from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, Base, get_db, Booking
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="NEXUS Space Tourism API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5174", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class BookingCreate(BaseModel):
    name: str
    email: str
    destination: str
    passengers: int
    pass_type: str

class BookingResponse(BookingCreate):
    id: str

@app.get("/api/health")
def health():
    return {"status": "OK", "service": "Space Tourism API"}

@app.post("/api/bookings", response_model=BookingResponse)
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    new_booking = Booking(
        id=str(uuid.uuid4()),
        name=booking.name,
        email=booking.email,
        destination=booking.destination,
        passengers=booking.passengers,
        pass_type=booking.pass_type
    )
    db.add(new_booking)
    await db.commit()
    return BookingResponse(id=new_booking.id, **booking.dict())
"""

# Dictionary to write
files_to_write = {
    "frontend/package.json": package_json,
    "frontend/vite.config.ts": vite_config,
    "frontend/tailwind.config.ts": tailwind_config,
    "frontend/postcss.config.js": postcss_config,
    "frontend/index.html": index_html,
    "frontend/src/main.tsx": main_tsx,
    "frontend/src/index.css": index_css,
    "frontend/src/App.tsx": app_tsx,
    "backend/requirements.txt": requirements_txt,
    "backend/database.py": database_py,
    "backend/main.py": main_py
}

# Write files
for rel_path, content in files_to_write.items():
    f_path = PROJECT_PATH / rel_path
    f_path.parent.mkdir(parents=True, exist_ok=True)
    f_path.write_text(content.strip(), encoding="utf-8")
    print(f"[OK] Written: {rel_path}")

print("Force-Scaffolding complete!")
