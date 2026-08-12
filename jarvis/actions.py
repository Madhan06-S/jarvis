import asyncio
import os
import re
import webbrowser


async def open_browser(url: str, browser: str = "chrome"):
    if not url.startswith("http"):
        url = "https://" + url if "." in url else f"https://www.google.com/search?q={url}"
    try:
        if browser.lower() == "brave":
            brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
            webbrowser.register('brave', None, webbrowser.BackgroundBrowser(brave_path))
            webbrowser.get('brave').open(url)
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)
    return {"success": True, "confirmation": f"Opened {url}"}


async def open_terminal(command: str = ""):
    try:
        if command:
            os.system(f'start "" cmd /c "{command}"')
        else:
            os.system('start cmd')
    except Exception as e:
        return {"success": False, "confirmation": str(e)}
    return {"success": True, "confirmation": "Terminal opened."}


def _generate_project_name(prompt: str) -> str:
    words = re.sub(r'[^a-zA-Z0-9 ]', '', prompt).split()
    return "-".join(w.lower() for w in words[:4])


async def _build_rich_fallback(prompt: str, port: int) -> str:
    """Generate a complete, real-looking professional website as fallback."""
    name = prompt.strip().title()
    slug = re.sub(r'[^a-z0-9]', '-', prompt.lower())[:30]
    return f'''[FILE: package.json]
```
{{
  "name": "{slug}",
  "version": "1.0.0",
  "description": "{name} - Professional Website",
  "scripts": {{"start": "node server.js", "dev": "node server.js"}},
  "dependencies": {{
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "sqlite3": "^5.1.6",
    "uuid": "^9.0.0",
    "body-parser": "^1.20.2"
  }}
}}
```
[FILE: server.js]
```
const express = require('express');
const cors = require('cors');
const path = require('path');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const {{ v4: uuidv4 }} = require('uuid');

const app = express();
const PORT = process.env.PORT || {port};

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// SQLite DB
const db = new sqlite3.Database('./data.db', (err) => {{
  if (err) console.error('DB error:', err);
  else console.log('Database connected.');
}});

db.serialize(() => {{
  db.run(`CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    service TEXT,
    date TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
}});

// API Routes
app.post('/api/contact', (req, res) => {{
  const {{ name, email, message }} = req.body;
  if (!name || !email) return res.status(400).json({{ error: 'Name and email required' }});
  const id = uuidv4();
  db.run('INSERT INTO contacts VALUES (?, ?, ?, ?, datetime("now"))', [id, name, email, message], (err) => {{
    if (err) return res.status(500).json({{ error: err.message }});
    res.json({{ success: true, id, message: 'Message received!' }});
  }});
}});

app.post('/api/booking', (req, res) => {{
  const {{ name, email, service, date }} = req.body;
  if (!name || !email) return res.status(400).json({{ error: 'Name and email required' }});
  const id = uuidv4();
  db.run('INSERT INTO bookings VALUES (?, ?, ?, ?, ?, datetime("now"))', [id, name, email, service, date], (err) => {{
    if (err) return res.status(500).json({{ error: err.message }});
    res.json({{ success: true, id, message: 'Booking confirmed!' }});
  }});
}});

app.get('/api/contacts', (req, res) => {{
  db.all('SELECT * FROM contacts ORDER BY created_at DESC', [], (err, rows) => {{
    if (err) return res.status(500).json({{ error: err.message }});
    res.json(rows);
  }});
}});

app.get('/api/bookings', (req, res) => {{
  db.all('SELECT * FROM bookings ORDER BY created_at DESC', [], (err, rows) => {{
    if (err) return res.status(500).json({{ error: err.message }});
    res.json(rows);
  }});
}});

app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));

app.listen(PORT, () => console.log(`JARVIS | {name} running at http://localhost:${{PORT}}`));
```
[FILE: public/index.html]
```
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <!-- NAV -->
  <nav class="navbar" id="navbar">
    <div class="nav-container">
      <div class="nav-logo">
        <span class="logo-icon">⚡</span>
        <span class="logo-text">{name}</span>
      </div>
      <ul class="nav-links" id="navLinks">
        <li><a href="#home">Home</a></li>
        <li><a href="#about">About</a></li>
        <li><a href="#services">Services</a></li>
        <li><a href="#contact">Contact</a></li>
      </ul>
      <button class="nav-cta" onclick="scrollTo('#contact')">Get Started</button>
      <button class="hamburger" id="hamburger" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  </nav>

  <!-- HERO -->
  <section class="hero" id="home">
    <div class="hero-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-overlay"></div>
    </div>
    <div class="hero-content">
      <div class="hero-badge">
        <span class="badge-dot"></span>
        Professional · Premium · Powerful
      </div>
      <h1 class="hero-title">
        <span class="gradient-text">{name}</span>
      </h1>
      <p class="hero-sub">Built with precision. Designed for excellence. Powered by JARVIS.</p>
      <div class="hero-actions">
        <button class="btn-primary" onclick="document.querySelector('#contact').scrollIntoView({{behavior:'smooth'}})">
          Book Now
        </button>
        <button class="btn-ghost" onclick="document.querySelector('#services').scrollIntoView({{behavior:'smooth'}})">
          Our Services
        </button>
      </div>
      <div class="hero-stats">
        <div class="stat"><span class="stat-num" data-target="500">0</span><span class="stat-label">Clients</span></div>
        <div class="stat-divider"></div>
        <div class="stat"><span class="stat-num" data-target="98">0</span>%<span class="stat-label">Satisfaction</span></div>
        <div class="stat-divider"></div>
        <div class="stat"><span class="stat-num" data-target="10">0</span>+<span class="stat-label">Years</span></div>
      </div>
    </div>
    <div class="scroll-indicator">
      <div class="scroll-dot"></div>
      <span>Scroll</span>
    </div>
  </section>

  <!-- ABOUT -->
  <section class="about" id="about">
    <div class="container">
      <div class="section-header">
        <span class="section-tag">About Us</span>
        <h2>Excellence in <span class="gradient-text">Everything We Do</span></h2>
        <p>We deliver world-class services with a commitment to quality and customer satisfaction that sets us apart from the competition.</p>
      </div>
      <div class="about-grid">
        <div class="about-card">
          <div class="card-icon">🎯</div>
          <h3>Our Mission</h3>
          <p>To provide premium services that exceed expectations and create lasting value for every client we serve.</p>
        </div>
        <div class="about-card">
          <div class="card-icon">💎</div>
          <h3>Our Values</h3>
          <p>Integrity, excellence, and innovation guide every decision we make and every service we deliver.</p>
        </div>
        <div class="about-card">
          <div class="card-icon">🚀</div>
          <h3>Our Vision</h3>
          <p>To be the industry leader in our field, recognized globally for unmatched quality and impact.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- SERVICES -->
  <section class="services" id="services">
    <div class="container">
      <div class="section-header">
        <span class="section-tag">What We Offer</span>
        <h2>Our <span class="gradient-text">Services</span></h2>
        <p>Comprehensive solutions tailored to meet your unique needs and exceed your expectations.</p>
      </div>
      <div class="services-grid" id="servicesGrid">
        <div class="service-card featured">
          <div class="service-badge">Popular</div>
          <div class="service-icon">⭐</div>
          <h3>Premium Package</h3>
          <p>Our flagship service offering everything you need for complete success and peace of mind.</p>
          <ul class="service-features">
            <li>✓ Full-service support</li>
            <li>✓ Priority access</li>
            <li>✓ Dedicated manager</li>
            <li>✓ 24/7 availability</li>
          </ul>
          <button class="btn-primary" onclick="openBooking('Premium Package')">Book Now</button>
        </div>
        <div class="service-card">
          <div class="service-icon">💫</div>
          <h3>Standard Package</h3>
          <p>The perfect balance of quality and value for those who want the best without compromise.</p>
          <ul class="service-features">
            <li>✓ Core services</li>
            <li>✓ Regular support</li>
            <li>✓ Expert guidance</li>
          </ul>
          <button class="btn-outline" onclick="openBooking('Standard Package')">Book Now</button>
        </div>
        <div class="service-card">
          <div class="service-icon">🔥</div>
          <h3>Starter Package</h3>
          <p>Everything you need to get started on the right track toward achieving your goals.</p>
          <ul class="service-features">
            <li>✓ Essential features</li>
            <li>✓ Email support</li>
            <li>✓ Online resources</li>
          </ul>
          <button class="btn-outline" onclick="openBooking('Starter Package')">Book Now</button>
        </div>
      </div>
    </div>
  </section>

  <!-- TESTIMONIALS -->
  <section class="testimonials">
    <div class="container">
      <div class="section-header">
        <span class="section-tag">Reviews</span>
        <h2>What Our <span class="gradient-text">Clients Say</span></h2>
      </div>
      <div class="testimonials-grid">
        <div class="testimonial-card">
          <div class="stars">★★★★★</div>
          <p>"Absolutely outstanding service. The team went above and beyond to deliver exactly what we needed."</p>
          <div class="testimonial-author">
            <div class="author-avatar">JD</div>
            <div><strong>John Davis</strong><span>CEO, TechCorp</span></div>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="stars">★★★★★</div>
          <p>"Professional, reliable, and truly exceptional. We've been clients for 5 years and never looked back."</p>
          <div class="testimonial-author">
            <div class="author-avatar">SR</div>
            <div><strong>Sarah Rodriguez</strong><span>Director, InnovateCo</span></div>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="stars">★★★★★</div>
          <p>"The best in the industry. Their attention to detail and commitment to excellence is unmatched."</p>
          <div class="testimonial-author">
            <div class="author-avatar">MK</div>
            <div><strong>Michael Kim</strong><span>Founder, StartupX</span></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- CONTACT -->
  <section class="contact" id="contact">
    <div class="container">
      <div class="section-header">
        <span class="section-tag">Contact Us</span>
        <h2>Get in <span class="gradient-text">Touch</span></h2>
        <p>Ready to get started? We'd love to hear from you. Send us a message and we'll respond within 24 hours.</p>
      </div>
      <div class="contact-grid">
        <div class="contact-info">
          <div class="info-item"><span class="info-icon">📍</span><div><strong>Location</strong><p>Available Worldwide</p></div></div>
          <div class="info-item"><span class="info-icon">📧</span><div><strong>Email</strong><p>hello@{slug}.com</p></div></div>
          <div class="info-item"><span class="info-icon">📞</span><div><strong>Phone</strong><p>+1 (555) 000-0000</p></div></div>
          <div class="info-item"><span class="info-icon">🕐</span><div><strong>Hours</strong><p>Mon-Sun: 9AM - 9PM</p></div></div>
        </div>
        <form class="contact-form" id="contactForm">
          <div class="form-row">
            <div class="form-group">
              <label>Full Name *</label>
              <input type="text" id="cName" placeholder="John Smith" required>
            </div>
            <div class="form-group">
              <label>Email Address *</label>
              <input type="email" id="cEmail" placeholder="john@example.com" required>
            </div>
          </div>
          <div class="form-group">
            <label>Message</label>
            <textarea id="cMessage" rows="5" placeholder="How can we help you?"></textarea>
          </div>
          <button type="submit" class="btn-primary btn-full">Send Message →</button>
          <div class="form-status" id="formStatus"></div>
        </form>
      </div>
    </div>
  </section>

  <!-- BOOKING MODAL -->
  <div class="modal" id="bookingModal">
    <div class="modal-overlay" onclick="closeBooking()"></div>
    <div class="modal-content">
      <button class="modal-close" onclick="closeBooking()">✕</button>
      <h2>Book a <span class="gradient-text">Consultation</span></h2>
      <form id="bookingForm">
        <div class="form-group">
          <label>Service</label>
          <input type="text" id="bService" readonly>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Full Name *</label>
            <input type="text" id="bName" placeholder="Your name" required>
          </div>
          <div class="form-group">
            <label>Email *</label>
            <input type="email" id="bEmail" placeholder="Your email" required>
          </div>
        </div>
        <div class="form-group">
          <label>Preferred Date</label>
          <input type="date" id="bDate">
        </div>
        <button type="submit" class="btn-primary btn-full">Confirm Booking →</button>
        <div class="form-status" id="bookingStatus"></div>
      </form>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="footer">
    <div class="container">
      <div class="footer-top">
        <div class="footer-brand">
          <span class="logo-icon">⚡</span>
          <span class="logo-text">{name}</span>
          <p>Excellence delivered, every time.</p>
        </div>
        <div class="footer-links">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#services">Services</a>
          <a href="#contact">Contact</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© 2025 {name}. All rights reserved. Built by JARVIS.</p>
      </div>
    </div>
  </footer>

  <script src="js/main.js"></script>
</body>
</html>
```
[FILE: public/css/style.css]
```
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {{
  --bg: #050508;
  --bg2: #0a0a12;
  --bg3: #0f0f1a;
  --surface: rgba(255,255,255,0.04);
  --border: rgba(255,255,255,0.08);
  --border-glow: rgba(99,102,241,0.3);
  --primary: #6366f1;
  --primary-2: #8b5cf6;
  --accent: #06b6d4;
  --text: #f8f8ff;
  --text-muted: rgba(248,248,255,0.55);
  --radius: 16px;
  --radius-lg: 24px;
  --shadow: 0 25px 50px rgba(0,0,0,0.5);
  --glow: 0 0 60px rgba(99,102,241,0.15);
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; line-height:1.6; overflow-x:hidden; }}

.gradient-text {{
  background: linear-gradient(135deg, var(--primary), var(--accent));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}}

/* NAVBAR */
.navbar {{
  position:fixed; top:0; left:0; right:0; z-index:1000;
  padding:16px 0;
  transition: all 0.3s ease;
  border-bottom: 1px solid transparent;
}}
.navbar.scrolled {{
  background: rgba(5,5,8,0.95);
  backdrop-filter: blur(20px);
  border-color: var(--border);
}}
.nav-container {{
  max-width:1200px; margin:0 auto; padding:0 24px;
  display:flex; align-items:center; justify-content:space-between;
}}
.nav-logo {{ display:flex; align-items:center; gap:10px; font-size:1.3rem; font-weight:800; }}
.logo-icon {{ font-size:1.5rem; }}
.nav-links {{ display:flex; list-style:none; gap:32px; }}
.nav-links a {{ color:var(--text-muted); text-decoration:none; font-size:0.95rem; font-weight:500; transition:color 0.2s; }}
.nav-links a:hover {{ color:var(--text); }}
.nav-cta {{
  background:linear-gradient(135deg, var(--primary), var(--primary-2));
  border:none; color:#fff; padding:10px 24px; border-radius:50px;
  font-weight:600; cursor:pointer; font-size:0.9rem; transition:opacity 0.2s;
}}
.nav-cta:hover {{ opacity:0.85; }}
.hamburger {{ display:none; flex-direction:column; gap:5px; background:none; border:none; cursor:pointer; padding:4px; }}
.hamburger span {{ width:24px; height:2px; background:var(--text); border-radius:2px; transition:all 0.3s; }}

/* HERO */
.hero {{
  min-height:100vh; display:flex; align-items:center; justify-content:center;
  position:relative; text-align:center; padding:120px 24px 80px;
  overflow:hidden;
}}
.hero-bg {{ position:absolute; inset:0; z-index:0; }}
.orb {{
  position:absolute; border-radius:50%; filter:blur(80px); opacity:0.15; animation:pulse 8s ease-in-out infinite;
}}
.orb-1 {{ width:600px; height:600px; background:var(--primary); top:-200px; left:-200px; animation-delay:0s; }}
.orb-2 {{ width:500px; height:500px; background:var(--accent); bottom:-200px; right:-200px; animation-delay:3s; }}
.orb-3 {{ width:400px; height:400px; background:var(--primary-2); top:50%; left:50%; transform:translate(-50%,-50%); animation-delay:6s; }}
.grid-overlay {{
  position:absolute; inset:0;
  background-image: linear-gradient(rgba(99,102,241,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.05) 1px, transparent 1px);
  background-size:60px 60px;
}}
.hero-content {{ position:relative; z-index:1; max-width:900px; margin:0 auto; }}
.hero-badge {{
  display:inline-flex; align-items:center; gap:8px;
  background:var(--surface); border:1px solid var(--border-glow);
  padding:8px 20px; border-radius:50px; font-size:0.85rem; color:var(--text-muted);
  margin-bottom:32px; animation:fadeInUp 0.6s ease forwards;
}}
.badge-dot {{ width:8px; height:8px; background:var(--accent); border-radius:50%; animation:pulse 2s infinite; }}
.hero-title {{ font-size:clamp(2.5rem, 6vw, 5rem); font-weight:900; line-height:1.1; margin-bottom:24px; animation:fadeInUp 0.6s 0.1s ease both; }}
.hero-sub {{ font-size:1.2rem; color:var(--text-muted); max-width:600px; margin:0 auto 40px; animation:fadeInUp 0.6s 0.2s ease both; }}
.hero-actions {{ display:flex; gap:16px; justify-content:center; flex-wrap:wrap; margin-bottom:64px; animation:fadeInUp 0.6s 0.3s ease both; }}
.hero-stats {{ display:flex; align-items:center; justify-content:center; gap:32px; flex-wrap:wrap; animation:fadeInUp 0.6s 0.4s ease both; }}
.stat {{ text-align:center; }}
.stat-num {{ font-size:2rem; font-weight:800; color:var(--primary); }}
.stat-label {{ display:block; font-size:0.8rem; color:var(--text-muted); margin-top:4px; }}
.stat-divider {{ width:1px; height:40px; background:var(--border); }}
.scroll-indicator {{ position:absolute; bottom:32px; left:50%; transform:translateX(-50%); display:flex; flex-direction:column; align-items:center; gap:8px; color:var(--text-muted); font-size:0.8rem; animation:bounce 2s infinite; }}
.scroll-dot {{ width:6px; height:6px; background:var(--primary); border-radius:50%; }}

/* BUTTONS */
.btn-primary, .btn-ghost, .btn-outline {{
  padding:14px 32px; border-radius:50px; font-weight:600; font-size:0.95rem;
  cursor:pointer; border:none; transition:all 0.25s ease; text-decoration:none; display:inline-block;
}}
.btn-primary {{ background:linear-gradient(135deg, var(--primary), var(--primary-2)); color:#fff; box-shadow:0 4px 24px rgba(99,102,241,0.35); }}
.btn-primary:hover {{ transform:translateY(-2px); box-shadow:0 8px 32px rgba(99,102,241,0.5); }}
.btn-ghost {{ background:var(--surface); color:var(--text); border:1px solid var(--border); }}
.btn-ghost:hover {{ background:rgba(255,255,255,0.08); border-color:var(--border-glow); }}
.btn-outline {{ background:transparent; color:var(--primary); border:2px solid var(--primary); }}
.btn-outline:hover {{ background:rgba(99,102,241,0.1); }}
.btn-full {{ width:100%; text-align:center; }}

/* SECTIONS */
section {{ padding:100px 0; }}
.container {{ max-width:1200px; margin:0 auto; padding:0 24px; }}
.section-header {{ text-align:center; max-width:700px; margin:0 auto 64px; }}
.section-tag {{ background:rgba(99,102,241,0.15); color:var(--primary); padding:6px 16px; border-radius:50px; font-size:0.8rem; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; }}
.section-header h2 {{ font-size:clamp(1.8rem, 4vw, 3rem); font-weight:800; margin:16px 0; }}
.section-header p {{ color:var(--text-muted); font-size:1.05rem; }}

/* ABOUT */
.about {{ background:var(--bg2); }}
.about-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:24px; }}
.about-card {{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  padding:40px 32px; transition:all 0.3s ease;
}}
.about-card:hover {{ border-color:var(--border-glow); transform:translateY(-4px); box-shadow:var(--glow); }}
.card-icon {{ font-size:2.5rem; margin-bottom:20px; }}
.about-card h3 {{ font-size:1.3rem; font-weight:700; margin-bottom:12px; }}
.about-card p {{ color:var(--text-muted); line-height:1.7; }}

/* SERVICES */
.services-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:24px; }}
.service-card {{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  padding:40px 32px; position:relative; transition:all 0.3s ease;
}}
.service-card:hover {{ border-color:var(--border-glow); transform:translateY(-4px); }}
.service-card.featured {{ border-color:var(--primary); background:rgba(99,102,241,0.08); }}
.service-badge {{
  position:absolute; top:20px; right:20px;
  background:linear-gradient(135deg, var(--primary), var(--primary-2));
  color:#fff; padding:4px 12px; border-radius:50px; font-size:0.75rem; font-weight:700;
}}
.service-icon {{ font-size:2.5rem; margin-bottom:20px; }}
.service-card h3 {{ font-size:1.3rem; font-weight:700; margin-bottom:12px; }}
.service-card p {{ color:var(--text-muted); margin-bottom:24px; line-height:1.7; }}
.service-features {{ list-style:none; margin-bottom:32px; }}
.service-features li {{ padding:8px 0; color:var(--text-muted); font-size:0.9rem; border-bottom:1px solid var(--border); }}
.service-features li:last-child {{ border:none; }}

/* TESTIMONIALS */
.testimonials {{ background:var(--bg2); }}
.testimonials-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:24px; }}
.testimonial-card {{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  padding:32px; transition:all 0.3s ease;
}}
.testimonial-card:hover {{ border-color:var(--border-glow); }}
.stars {{ color:#fbbf24; font-size:1.2rem; margin-bottom:16px; letter-spacing:2px; }}
.testimonial-card p {{ color:var(--text-muted); line-height:1.7; margin-bottom:24px; font-style:italic; }}
.testimonial-author {{ display:flex; align-items:center; gap:12px; }}
.author-avatar {{
  width:48px; height:48px; border-radius:50%;
  background:linear-gradient(135deg, var(--primary), var(--accent));
  display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:0.9rem;
}}
.testimonial-author strong {{ display:block; font-weight:600; }}
.testimonial-author span {{ font-size:0.85rem; color:var(--text-muted); }}

/* CONTACT */
.contact-grid {{ display:grid; grid-template-columns:1fr 2fr; gap:48px; align-items:start; }}
.contact-info {{ display:flex; flex-direction:column; gap:28px; }}
.info-item {{ display:flex; gap:16px; align-items:flex-start; }}
.info-icon {{ font-size:1.5rem; flex-shrink:0; }}
.info-item strong {{ display:block; font-weight:600; margin-bottom:4px; }}
.info-item p {{ color:var(--text-muted); font-size:0.9rem; }}
.contact-form {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); padding:40px; }}
.form-row {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
.form-group {{ margin-bottom:20px; }}
.form-group label {{ display:block; margin-bottom:8px; font-size:0.9rem; font-weight:500; color:var(--text-muted); }}
.form-group input, .form-group textarea, .form-group select {{
  width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border);
  border-radius:12px; padding:12px 16px; color:var(--text); font-family:inherit;
  font-size:0.95rem; transition:border-color 0.2s;
}}
.form-group input:focus, .form-group textarea:focus {{
  outline:none; border-color:var(--primary); background:rgba(99,102,241,0.08);
}}
.form-group textarea {{ resize:vertical; min-height:120px; }}
.form-status {{ margin-top:16px; padding:12px 16px; border-radius:12px; font-size:0.9rem; display:none; text-align:center; }}
.form-status.success {{ background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); display:block; }}
.form-status.error {{ background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3); display:block; }}

/* MODAL */
.modal {{ display:none; position:fixed; inset:0; z-index:2000; }}
.modal.active {{ display:flex; align-items:center; justify-content:center; padding:24px; }}
.modal-overlay {{ position:absolute; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); }}
.modal-content {{
  position:relative; background:var(--bg3); border:1px solid var(--border-glow);
  border-radius:var(--radius-lg); padding:48px; max-width:560px; width:100%; z-index:1;
  animation:modalIn 0.3s ease;
}}
.modal-close {{
  position:absolute; top:20px; right:20px; background:var(--surface); border:1px solid var(--border);
  width:36px; height:36px; border-radius:50%; cursor:pointer; color:var(--text);
  display:flex; align-items:center; justify-content:center; font-size:1rem;
}}
.modal-close:hover {{ background:rgba(255,255,255,0.1); }}
.modal-content h2 {{ font-size:1.8rem; font-weight:800; margin-bottom:32px; }}

/* FOOTER */
.footer {{ background:var(--bg2); border-top:1px solid var(--border); padding:64px 0 32px; }}
.footer-top {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:40px; flex-wrap:wrap; gap:24px; }}
.footer-brand p {{ color:var(--text-muted); font-size:0.9rem; margin-top:8px; }}
.footer-links {{ display:flex; gap:24px; flex-wrap:wrap; }}
.footer-links a {{ color:var(--text-muted); text-decoration:none; font-size:0.9rem; transition:color 0.2s; }}
.footer-links a:hover {{ color:var(--text); }}
.footer-bottom {{ border-top:1px solid var(--border); padding-top:24px; color:var(--text-muted); font-size:0.85rem; text-align:center; }}

/* ANIMATIONS */
@keyframes fadeInUp {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes pulse {{ 0%,100% {{ opacity:0.15; transform:scale(1); }} 50% {{ opacity:0.25; transform:scale(1.1); }} }}
@keyframes bounce {{ 0%,100% {{ transform:translateX(-50%) translateY(0); }} 50% {{ transform:translateX(-50%) translateY(-8px); }} }}
@keyframes modalIn {{ from {{ opacity:0; transform:scale(0.95); }} to {{ opacity:1; transform:scale(1); }} }}

.animate-in {{ animation:fadeInUp 0.6s ease both; }}

/* RESPONSIVE */
@media(max-width:768px) {{
  .nav-links {{ display:none; }}
  .nav-links.open {{ display:flex; flex-direction:column; position:absolute; top:70px; left:0; right:0; background:rgba(5,5,8,0.98); padding:20px 24px; border-bottom:1px solid var(--border); gap:20px; }}
  .hamburger {{ display:flex; }}
  .contact-grid {{ grid-template-columns:1fr; }}
  .form-row {{ grid-template-columns:1fr; }}
  .hero-actions {{ flex-direction:column; align-items:center; }}
}}
```
[FILE: public/js/main.js]
```
// JARVIS Auto-Generated Website JS
document.addEventListener('DOMContentLoaded', () => {{

  // Navbar scroll effect
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {{
    navbar.classList.toggle('scrolled', window.scrollY > 50);
  }});

  // Hamburger menu
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('navLinks');
  if (hamburger) {{
    hamburger.addEventListener('click', () => {{
      navLinks.classList.toggle('open');
    }});
  }}

  // Animate stats counter
  const counters = document.querySelectorAll('.stat-num');
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        const el = entry.target;
        const target = +el.dataset.target;
        let count = 0;
        const inc = target / 60;
        const timer = setInterval(() => {{
          count += inc;
          if (count >= target) {{ el.textContent = target; clearInterval(timer); }}
          else {{ el.textContent = Math.ceil(count); }}
        }}, 20);
        observer.unobserve(el);
      }}
    }});
  }});
  counters.forEach(c => observer.observe(c));

  // Scroll animations
  const animObserver = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{ e.target.classList.add('animate-in'); animObserver.unobserve(e.target); }}
    }});
  }}, {{ threshold: 0.15 }});
  document.querySelectorAll('.about-card, .service-card, .testimonial-card').forEach(el => animObserver.observe(el));

  // Contact form
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {{
    contactForm.addEventListener('submit', async (e) => {{
      e.preventDefault();
      const status = document.getElementById('formStatus');
      const btn = contactForm.querySelector('button[type=submit]');
      btn.textContent = 'Sending...'; btn.disabled = true;
      try {{
        const res = await fetch('/api/contact', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            name: document.getElementById('cName').value,
            email: document.getElementById('cEmail').value,
            message: document.getElementById('cMessage').value
          }})
        }});
        const data = await res.json();
        if (data.success) {{
          status.className = 'form-status success';
          status.textContent = '✓ Message sent! We\'ll be in touch soon.';
          contactForm.reset();
        }} else {{
          throw new Error(data.error || 'Failed');
        }}
      }} catch(err) {{
        status.className = 'form-status error';
        status.textContent = '✕ ' + (err.message || 'Something went wrong. Please try again.');
      }}
      btn.textContent = 'Send Message →'; btn.disabled = false;
    }});
  }}

  // Booking modal
  window.openBooking = (service) => {{
    document.getElementById('bService').value = service;
    document.getElementById('bookingModal').classList.add('active');
    document.body.style.overflow = 'hidden';
  }};
  window.closeBooking = () => {{
    document.getElementById('bookingModal').classList.remove('active');
    document.body.style.overflow = '';
  }};

  const bookingForm = document.getElementById('bookingForm');
  if (bookingForm) {{
    bookingForm.addEventListener('submit', async (e) => {{
      e.preventDefault();
      const status = document.getElementById('bookingStatus');
      const btn = bookingForm.querySelector('button[type=submit]');
      btn.textContent = 'Booking...'; btn.disabled = true;
      try {{
        const res = await fetch('/api/booking', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            name: document.getElementById('bName').value,
            email: document.getElementById('bEmail').value,
            service: document.getElementById('bService').value,
            date: document.getElementById('bDate').value
          }})
        }});
        const data = await res.json();
        if (data.success) {{
          status.className = 'form-status success';
          status.textContent = '✓ Booking confirmed! We\'ll contact you shortly.';
          bookingForm.reset();
          setTimeout(() => closeBooking(), 2000);
        }} else {{
          throw new Error(data.error || 'Failed');
        }}
      }} catch(err) {{
        status.className = 'form-status error';
        status.textContent = '✕ ' + (err.message || 'Something went wrong.');
      }}
      btn.textContent = 'Confirm Booking →'; btn.disabled = false;
    }});
  }}

  // Smooth scroll
  window.scrollTo = (selector) => {{
    const el = document.querySelector(selector);
    if (el) el.scrollIntoView({{ behavior: 'smooth' }});
  }};

  // Active nav link on scroll
  const sections = document.querySelectorAll('section[id]');
  window.addEventListener('scroll', () => {{
    let current = '';
    sections.forEach(s => {{
      if (window.scrollY >= s.offsetTop - 100) current = s.id;
    }});
    document.querySelectorAll('.nav-links a').forEach(a => {{
      a.style.color = a.getAttribute('href') === '#' + current
        ? 'var(--text)' : 'var(--text-muted)';
    }});
  }});

}});
```'''


async def open_claude_in_project(project_dir: str, prompt: str, ws=None):
    import httpx
    import socket

    os.makedirs(project_dir, exist_ok=True)
    if ws:
        await ws.send_json({"type": "process_update", "message": f"Initializing: {os.path.basename(project_dir)}"})
    print(f"JARVIS BUILD: {project_dir}")

    # ── Pick a free port ──────────────────────────────────────────────────────
    def find_free_port(start=4000, end=4999) -> int:
        for p in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", p))
                    return p
                except OSError:
                    continue
        return 4000

    port = find_free_port()

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = (
        "You are not a beginner web generator anymore.\n"
        "You are JARVIS — an elite AI full-stack architect inspired by Iron Man technology.\n\n"
        "Whenever I give a website idea, you must first deeply analyze:\n"
        "- brand identity, modern UI/UX trends, futuristic interactions, premium SaaS design patterns, 3D visuals, responsiveness.\n"
        "Generate a COMPLETE high-end production-ready website automatically.\n"
        "IMPORTANT RULES:\n"
        "1. NEVER generate simple/basic layouts or plain bootstrap-like pages.\n"
        "2. Every website must feel like a premium Apple + Tesla + Iron Man level product.\n"
        "3. Every page should look award-winning like Awwwards websites.\n\n"
        "Use ONLY the following ultra-strict format for every file — nothing else:\n\n"
        "[FILE: relative/path/filename.ext]\n"
        "```\n"
        "<complete file content here>\n"
        "```\n\n"
        f"MANDATORY FILES (server must use port {port}):\n"
        "1. package.json — include 'express', 'cors', 'sqlite3', 'uuid' dependencies; 'start': 'node server.js'\n"
        f"2. server.js — Express server listening on process.env.PORT || {port}, serve static files from 'public/'\n"
        "3. public/index.html — STUNNING premium dark-themed frontend, glassmorphism, animations, full interactivity\n"
        "4. public/css/style.css — Premium dark design: gradients, smooth animations, modern Google Font\n"
        "5. public/js/main.js — Complete interactive JS — no TODOs, fully functional\n"
        "CRITICAL OUTPUT RULES:\n"
        "- Output ZERO conversational text or explanations\n"
        "- Output ONLY [FILE: path] blocks with complete code inside triple backticks\n"
        "- Every file must be 100% complete — no placeholders"
    )

    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Build complete full-stack website for: {prompt}"}
    ]

    # ── Call Pollinations with 3 retries ─────────────────────────────────────
    text_out = ""
    if ws:
        await ws.send_json({"type": "process_update", "message": "Generating full-stack code via AI (may take 1-2 mins)..."})

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=240.0) as client:
                res = await client.post(
                    "https://text.pollinations.ai/",
                    json={"messages": msgs, "model": "openai-large"},
                    headers={"Content-Type": "application/json", "User-Agent": "JARVIS-Builder/2.0"}
                )
                if res.status_code == 200 and "[FILE:" in res.text:
                    text_out = res.text
                    if ws:
                        await ws.send_json({"type": "process_update", "message": "Code generated. Parsing files..."})
                    break
                else:
                    print(f"Attempt {attempt + 1} — status={res.status_code}, has_files={'[FILE:' in res.text}")
        except Exception as e:
            print(f"Build attempt {attempt + 1} error: {e}")
        await asyncio.sleep(2)

    # ── Rich fallback — a REAL premium full-stack website ────────────────────
    if "[FILE:" not in text_out:
        if ws:
            await ws.send_json({"type": "process_update", "message": "Generating premium website from built-in template..."})
        text_out = await _build_rich_fallback(prompt, port)


    # ── Write files to disk ───────────────────────────────────────────────────
    if ws:
        await ws.send_json({"type": "process_update", "message": "Writing project files to disk..."})

    file_blocks = re.split(r'\[FILE:\s*(.+?)\]', text_out)
    files_written = 0

    for i in range(1, len(file_blocks), 2):
        file_path = file_blocks[i].strip().strip('"').strip("'")
        content_block = file_blocks[i + 1] if i + 1 < len(file_blocks) else ""
        code_match = re.search(r'```(?:[a-zA-Z0-9]*)\n?(.*?)```', content_block, re.DOTALL)
        code = code_match.group(1).strip() if code_match else content_block.strip()
        if ".." in file_path or not file_path:
            continue
        full_path = os.path.join(project_dir, file_path.replace("/", os.sep))
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
        files_written += 1
        print(f"  WROTE: {file_path}")

    if ws:
        await ws.send_json({"type": "process_update", "message": f"Wrote {files_written} files. Running npm install..."})

    # ── npm install (fully async, no subprocess.PIPE conflict) ───────────────
    try:
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        install_proc = await asyncio.create_subprocess_exec(
            npm_cmd, "install",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, install_err = await asyncio.wait_for(install_proc.communicate(), timeout=120)
        if install_proc.returncode and install_proc.returncode != 0:
            print("npm install stderr:", install_err.decode()[:400])
        else:
            print("npm install: OK")
    except asyncio.TimeoutError:
        print("npm install timed out after 120s")
    except Exception as e:
        print(f"npm install error: {e}")

    # ── Launch Node.js in a new visible CMD window ───────────────────────────
    if ws:
        await ws.send_json({"type": "process_update", "message": f"Starting Node.js server on port {port}..."})
    try:
        project_name = os.path.basename(project_dir)
        launch_cmd = (
            f'start "JARVIS | {project_name}" cmd /k '
            f'"cd /d {project_dir} && set PORT={port} && node server.js"'
        )
        os.system(launch_cmd)
    except Exception as e:
        print(f"Server launch error: {e}")

    # ── Wait for server to actually be reachable ─────────────────────────────
    import socket as _sock
    if ws:
        await ws.send_json({"type": "process_update", "message": "Waiting for server to come online..."})

    for _ in range(25):
        await asyncio.sleep(1)
        try:
            with _sock.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            pass

    url = f"http://localhost:{port}"
    webbrowser.open(url)

    if ws:
        await ws.send_json({"type": "process_update", "message": f"LIVE at {url}"})
        await ws.send_json({"type": "process_complete"})
        await ws.send_json({"type": "browser_speak", "text": f"Your project is live on port {port}, sir."})

    print(f"JARVIS BUILD COMPLETE: {url}")
    return {"success": True, "confirmation": f"Project built and running at {url}", "url": url}


async def rewrite_own_code(prompt: str):
    import httpx
    print(f"JARVIS AGENT: Self-modification initiated for: {prompt}")

    files_to_read = [
        "actions.py", "server.py",
        "frontend/index.html", "frontend/src/orb.ts",
        "frontend/src/main.ts", "frontend/src/style.css"
    ]
    context = ""
    for f in files_to_read:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                context += f"\n--- {f} ---\n{fh.read()}\n"
        except Exception:
            pass

    system_prompt = (
        "You are AntiGravity, the core coder component of JARVIS. Rewrite JARVIS's source code.\n"
        "Identify the ONE file that needs to be modified.\n"
        "Format output EXACTLY:\n"
        "FILE: <filepath>\n"
        "```\n"
        "<full updated code>\n"
        "```\n"
        "NO explanations. Complete replacement code only. Never truncate."
    )

    msgs = [
        {"role": "system", "content": system_prompt + "\n\nCurrent Source:\n" + context},
        {"role": "user", "content": f"Update my code to do this: {prompt}"}
    ]

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            res = await client.post(
                "https://text.pollinations.ai/",
                json={"messages": msgs, "model": "openai"},
                headers={"Content-Type": "application/json"}
            )
            text_out = res.text
    except Exception as e:
        print("Self-rewrite error:", e)
        return {"success": False, "confirmation": f"Self-modification failed: {e}"}

    file_match = re.search(r'FILE:\s*([^\n]+)', text_out)
    code_match = re.search(r'```(?:[a-zA-Z]*)\n(.*?)```', text_out, re.DOTALL)

    if file_match and code_match:
        file_path = file_match.group(1).strip()
        new_code = code_match.group(1)
        if ".." in file_path or not os.path.exists(file_path):
            print(f"Invalid or unknown file path: {file_path}")
            return {"success": False, "confirmation": "Agent predicted an invalid file path."}
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)
        print(f"JARVIS AGENT: Overwrote {file_path} successfully.")
        return {"success": True, "confirmation": f"Rewritten {file_path} as requested, sir."}
    else:
        print("Agent failed to provide correct format.")
        return {"success": False, "confirmation": "Failed to generate the code block correctly, sir."}


async def search_web_for_user(query: str):
    import urllib.parse
    q = urllib.parse.quote(query)
    webbrowser.open(f"https://duckduckgo.com/?q={q}")
    return {"success": True, "confirmation": "Opened search overlay."}


async def generate_image_for_user(query: str):
    import urllib.parse
    q = urllib.parse.quote(query)
    webbrowser.open(f"https://image.pollinations.ai/prompt/{q}?nologo=true&enhance=true")
    return {"success": True, "confirmation": "Opened generated imagery window."}


async def prompt_existing_terminal(project_name: str, prompt: str):
    print(f"Mocking prompt to {project_name}: {prompt}")
    return {"success": False, "confirmation": "Cannot prompt existing terminal natively on Windows."}


async def get_chrome_tab_info():
    return {"title": "", "url": ""}


async def monitor_build(project_dir: str, ws, synthesize_fn):
    marker = os.path.join(project_dir, '.jarvis_output.txt')
    timeout = 600
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        if os.path.exists(marker):
            with open(marker, 'r') as f:
                output = f.read()
            if "Done" in output or "Success" in output:
                await ws.send_json({"type": "task_complete", "name": os.path.basename(project_dir), "summary": "Build finished."})
                await synthesize_fn(ws, f"The build for {os.path.basename(project_dir)} has completed, sir.")
                return
        await asyncio.sleep(2)


async def execute_action(intent: dict, projects: list, ws=None):
    action = intent.get('action')
    target = intent.get('target', '')

    if action == "BUILD":
        import builder
        res = await builder.build_fullstack_project(target, ws)
        if res.get("status") == "ok":
            return {"success": True, "confirmation": f"Project built and running at {res.get('url')}", "url": res.get('url')}
        else:
            return {"success": False, "confirmation": f"Build failed: {res.get('error')}"}

    if action == "MODIFY_PROJECT":
        import builder
        res = await builder.modify_project(target, ws)
        return {"success": res.get("status") == "ok", "confirmation": "Modified."}

    if action == "DEPLOY_PROJECT":
        import builder
        res = await builder.deploy_project(ws)
        return {"success": res.get("status") == "ok", "confirmation": "Deployed."}

    if action == "BROWSE":
        return await open_browser(target)

    if action == "BROWSE_BRAVE":
        return await open_browser(target, browser="brave")

    if action == "OPEN_TERMINAL":
        return await open_terminal()

    if action == "REWRITE_CODE":
        return await rewrite_own_code(target)

    if action == "PROMPT_PROJECT":
        parts = target.split('|||')
        if len(parts) >= 2:
            return await prompt_existing_terminal(parts[0].strip(), parts[1].strip())

    return {"success": False, "confirmation": "Unknown action."}
