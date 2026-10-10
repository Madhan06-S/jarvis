"""Real multi-page business website fallback — replaces generic PULSE dashboard."""

import json
import re


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "", (title or "nexus").lower())
    return s[:20] or "nexus"


def build_business_fallback(title: str, description: str = "") -> dict:
    brand = (title or "Nexus").strip()[:40]
    slug = _slug(brand)
    desc = (description or f"{brand} delivers premium digital experiences.").strip()[:200]

    low = (description or "").lower()
    if "analyzer" in low or "analysis" in low:
        services = [
            {"id": 1, "name": "URL Performance Scan", "description": "Speed, Core Web Vitals, and mobile readiness.", "price": "Free", "category": "Audit"},
            {"id": 2, "name": "SEO & Metadata Review", "description": "Titles, descriptions, headings, and indexability.", "price": "Free", "category": "SEO"},
            {"id": 3, "name": "Accessibility Check", "description": "WCAG contrast, alt text, and keyboard navigation.", "price": "Pro", "category": "A11y"},
            {"id": 4, "name": "Security Headers", "description": "HTTPS, CSP, and common vulnerability patterns.", "price": "Pro", "category": "Security"},
        ]
    else:
        services = [
            {"id": 1, "name": "Strategy & Consulting", "description": "Roadmaps, audits, and growth planning.", "price": "From $2,500", "category": "Consulting"},
            {"id": 2, "name": "Design & Branding", "description": "Visual identity, UI/UX, and motion design.", "price": "From $1,800", "category": "Creative"},
            {"id": 3, "name": "Web Development", "description": "Fast, accessible React apps with real APIs.", "price": "From $4,200", "category": "Engineering"},
            {"id": 4, "name": "SEO & Marketing", "description": "Content, analytics, and conversion optimization.", "price": "From $900/mo", "category": "Growth"},
        ]
    testimonials = [
        {"id": 1, "name": "Sarah Chen", "role": "CEO, Vertex Labs", "quote": f"{brand} transformed our online presence in six weeks."},
        {"id": 2, "name": "Marcus Webb", "role": "Founder, Orbit Health", "quote": "Professional, fast, and every page connects to real data."},
        {"id": 3, "name": "Priya Nair", "role": "Director, Bloom Retail", "quote": "The best agency experience we have had — highly recommended."},
    ]
    team = [
        {"id": 1, "name": "Alex Rivera", "role": "Creative Director"},
        {"id": 2, "name": "Jordan Lee", "role": "Lead Engineer"},
        {"id": 3, "name": "Sam Okonkwo", "role": "Growth Strategist"},
    ]

    app = f'''import React, {{ useState, useEffect }} from 'react';
import {{ motion, AnimatePresence }} from 'framer-motion';
import {{ ArrowRight, Mail, Phone, MapPin, Star, Zap, CheckCircle2, Menu, X }} from 'lucide-react';

const BRAND = "{brand}";

export default function App() {{
  const [page, setPage] = useState('home');
  const [menuOpen, setMenuOpen] = useState(false);
  const [services, setServices] = useState([]);
  const [testimonials, setTestimonials] = useState([]);
  const [team, setTeam] = useState([]);
  const [form, setForm] = useState({{ name: '', email: '', message: '' }});
  const [sent, setSent] = useState(false);

  useEffect(() => {{
    fetch('/api/services').then(r => r.json()).then(setServices).catch(() => {{}});
    fetch('/api/testimonials').then(r => r.json()).then(setTestimonials).catch(() => {{}});
    fetch('/api/team').then(r => r.json()).then(setTeam).catch(() => {{}});
  }}, []);

  const submitContact = (e) => {{
    e.preventDefault();
    fetch('/api/contact', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(form),
    }}).then(() => {{ setSent(true); setForm({{ name: '', email: '', message: '' }}); }});
  }};

  const nav = ['home', 'services', 'about', 'contact'];

  return (
    <motion.div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <button onClick={{() => setPage('home')}} className="flex items-center gap-2">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center"><Zap className="w-5 h-5 text-white" /></div>
            <span className="text-xl font-black">{{BRAND}}</span>
          </button>
          <div className="hidden md:flex gap-8 text-sm font-medium">
            {{nav.map(p => (
              <button key={{p}} onClick={{() => setPage(p)}} className={{page === p ? 'text-indigo-400' : 'text-zinc-400 hover:text-white'}}>
                {{p.charAt(0).toUpperCase() + p.slice(1)}}
              </button>
            ))}}
          </div>
          <button className="md:hidden" onClick={{() => setMenuOpen(!menuOpen)}}>{{menuOpen ? <X /> : <Menu />}}</button>
        </div>
      </nav>

      <main className="pt-20">
        <AnimatePresence mode="wait">
          {{page === 'home' && (
            <motion.div key="home" initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} exit={{{{ opacity: 0 }}}}>
              <section className="relative min-h-[80vh] flex items-center">
                <motion.div className="absolute inset-0 bg-gradient-to-br from-indigo-900/30 to-zinc-950" />
                <div className="max-w-7xl mx-auto px-6 relative z-10 py-24">
                  <h1 className="text-5xl md:text-7xl font-black tracking-tighter max-w-3xl mb-6">
                    {desc.split(".")[0]}.
                  </h1>
                  <p className="text-xl text-zinc-400 max-w-xl mb-10">{desc}</p>
                  <button onClick={{() => setPage('services')}} className="bg-white text-zinc-950 px-8 py-4 rounded-full font-bold inline-flex items-center gap-2 hover:scale-105 transition-transform">
                    View Services <ArrowRight className="w-5 h-5" />
                  </button>
                </div>
              </section>
              <section className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
                {{services.slice(0, 3).map(s => (
                  <div key={{s.id}} className="p-6 rounded-2xl bg-zinc-900/50 border border-white/5">
                    <h3 className="font-bold text-lg mb-2">{{s.name}}</h3>
                    <p className="text-zinc-400 text-sm">{{s.description}}</p>
                    <p className="text-indigo-400 font-bold mt-3">{{s.price}}</p>
                  </div>
                ))}}
              </section>
            </motion.div>
          )}}
          {{page === 'services' && (
            <motion.div key="svc" className="max-w-7xl mx-auto px-6 py-16">
              <h2 className="text-4xl font-black mb-10">Services</h2>
              <div className="grid md:grid-cols-2 gap-6">
                {{services.map(s => (
                  <div key={{s.id}} className="p-6 rounded-2xl bg-zinc-900/50 border border-white/5 hover:border-indigo-500/40 transition-colors">
                    <h3 className="text-xl font-bold">{{s.name}}</h3>
                    <p className="text-zinc-400 mt-2">{{s.description}}</p>
                    <p className="text-indigo-400 font-bold mt-4">{{s.price}}</p>
                  </div>
                ))}}
              </div>
            </motion.div>
          )}}
          {{page === 'about' && (
            <motion.div key="about" className="max-w-7xl mx-auto px-6 py-16">
              <h2 className="text-4xl font-black mb-6">About {{BRAND}}</h2>
              <p className="text-zinc-400 max-w-2xl text-lg mb-12">{desc}</p>
              <div className="grid md:grid-cols-3 gap-6">
                {{team.map(m => (
                  <div key={{m.id}} className="p-6 rounded-2xl bg-zinc-900/50 border border-white/5 text-center">
                    <div className="w-16 h-16 rounded-full bg-indigo-600 mx-auto mb-4 flex items-center justify-center text-xl font-bold">{{m.name[0]}}</div>
                    <h3 className="font-bold">{{m.name}}</h3>
                    <p className="text-indigo-400 text-sm">{{m.role}}</p>
                  </div>
                ))}}
              </div>
            </motion.div>
          )}}
          {{page === 'contact' && (
            <motion.div key="contact" className="max-w-xl mx-auto px-6 py-16">
              <h2 className="text-4xl font-black mb-8">Contact</h2>
              {{sent ? (
                <div className="p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex gap-3 items-center">
                  <CheckCircle2 className="text-emerald-400" /> Message sent successfully.
                </div>
              ) : (
                <form onSubmit={{submitContact}} className="space-y-4">
                  <input required className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10" placeholder="Name" value={{form.name}} onChange={{e => setForm(f => ({{...f, name: e.target.value}}))}} />
                  <input required type="email" className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10" placeholder="Email" value={{form.email}} onChange={{e => setForm(f => ({{...f, email: e.target.value}}))}} />
                  <textarea required rows={{5}} className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10" placeholder="Message" value={{form.message}} onChange={{e => setForm(f => ({{...f, message: e.target.value}}))}} />
                  <button type="submit" className="w-full py-4 bg-indigo-600 rounded-xl font-bold hover:bg-indigo-500">Send</button>
                </form>
              )}}
            </motion.div>
          )}}
        </AnimatePresence>
        {{page === 'home' && testimonials.length > 0 && (
          <section className="max-w-7xl mx-auto px-6 py-16 border-t border-white/5">
            <h2 className="text-2xl font-black mb-8 text-center">Client Stories</h2>
            <motion.div className="grid md:grid-cols-3 gap-6">
              {{testimonials.map(t => (
                <div key={{t.id}} className="p-6 rounded-2xl bg-zinc-900/50 border border-white/5">
                  <div className="flex gap-1 mb-3">{{[1,2,3,4,5].map(n => <Star key={{n}} className="w-4 h-4 fill-amber-400 text-amber-400" />)}}</div>
                  <p className="text-zinc-300 mb-3">"{{t.quote}}"</p>
                  <p className="font-bold">{{t.name}}</p>
                  <p className="text-xs text-zinc-500">{{t.role}}</p>
                </div>
              ))}}
            </motion.div>
          </section>
        )}}
      </main>
    </motion.div>
  );
}}'''

    backend = f'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="{brand} API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SERVICES = {json.dumps(services)}
TESTIMONIALS = {json.dumps(testimonials)}
TEAM = {json.dumps(team)}
CONTACTS = []

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

@app.get("/api/health")
def health():
    return {{"status": "OK", "brand": "{brand}"}}

@app.get("/api/services")
def list_services():
    return SERVICES

@app.get("/api/testimonials")
def list_testimonials():
    return TESTIMONIALS

@app.get("/api/team")
def list_team():
    return TEAM

@app.post("/api/contact")
def contact(data: ContactForm):
    CONTACTS.append(data.dict())
    return {{"ok": True, "message": "Thanks! We received your message."}}
'''

    return {"app": app, "backend": backend}
