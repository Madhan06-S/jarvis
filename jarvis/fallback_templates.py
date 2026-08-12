"""Hardcoded fallback apps — deployed when AI generation fails."""

_ECOMMERCE = """import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingBag, Star, Zap, ArrowRight, X, Menu, Search, CreditCard } from 'lucide-react';

const PRODUCTS = [
  { id: 1, name: "Neon Chronograph", price: 299, img: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80", tag: "NEW" },
  { id: 2, name: "Urban Backpack", price: 129, img: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&q=80", tag: "BESTSELLER" },
  { id: 3, name: "Aero Sneakers", price: 189, img: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80", tag: "TRENDING" },
  { id: 4, name: "Minimalist Shades", price: 89, img: "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&q=80", tag: "LIMITED" }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [cart, setCart] = useState([]);
  const addToCart = (p) => setCart(c => [...c, p]);
  const total = cart.reduce((a, b) => a + b.price, 0);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30 overflow-x-hidden">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setActiveTab('home')}>
            <div className="w-10 h-10 bg-indigo-600 flex items-center justify-center rounded-lg rotate-3">
              <Zap className="w-6 h-6 text-white -rotate-3" />
            </div>
            <span className="text-2xl font-black tracking-tighter text-white uppercase">NEXUS<span className="text-indigo-500">.</span></span>
          </div>
          <button onClick={() => setActiveTab('cart')} className="flex items-center gap-2 bg-white/5 hover:bg-white/10 px-4 py-2 rounded-full transition-colors border border-white/5">
            <ShoppingBag className="w-5 h-5 text-indigo-400" />
            <span className="font-bold">{cart.length}</span>
          </button>
        </div>
      </nav>
      <main className="pt-20">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="relative min-h-[70vh] flex items-center">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/20 to-zinc-950 z-0" />
                <div className="max-w-7xl mx-auto px-6 relative z-10 py-20 w-full">
                  <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold tracking-widest mb-6 rounded-full">
                      <Star className="w-3 h-3" /> NEW COLLECTION
                    </div>
                    <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-[0.9] mb-6">DEFINE YOUR <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">STYLE</span></h1>
                    <p className="text-lg text-zinc-400 mb-10 max-w-xl">Curated streetwear and accessories for the modern urban explorer. Engineered for life.</p>
                    <button className="bg-white text-zinc-950 px-8 py-4 font-black tracking-wider hover:scale-105 transition-transform flex items-center gap-2 rounded-full">
                      SHOP NOW <ArrowRight className="w-5 h-5" />
                    </button>
                  </motion.div>
                </div>
              </div>
              <div className="py-24 bg-zinc-950 max-w-7xl mx-auto px-6">
                <h2 className="text-3xl font-black tracking-tight mb-12">FEATURED DROPS</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {PRODUCTS.map((p, i) => (
                    <motion.div key={p.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} className="group cursor-pointer">
                      <div className="relative h-80 bg-zinc-900 rounded-2xl overflow-hidden mb-4">
                        <img src={p.img} alt={p.name} className="w-full h-full object-cover grayscale transition-all duration-500 group-hover:grayscale-0 group-hover:scale-110" />
                        <div className="absolute top-4 left-4 bg-zinc-950/80 backdrop-blur text-white px-3 py-1 text-xs font-bold rounded-full border border-white/10">{p.tag}</div>
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                           <button onClick={(e) => { e.stopPropagation(); addToCart(p); }} className="bg-indigo-600 text-white px-6 py-3 font-bold rounded-full hover:bg-indigo-500 hover:scale-105 transition-all">ADD TO CART</button>
                        </div>
                      </div>
                      <h3 className="text-lg font-bold">{p.name}</h3>
                      <p className="text-indigo-400 font-bold">${p.price}</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
          {activeTab === 'cart' && (
            <motion.div key="cart" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="min-h-screen py-20 px-6 max-w-4xl mx-auto">
              <h1 className="text-4xl font-black tracking-tighter mb-12 flex items-center gap-4"><ShoppingBag className="w-8 h-8 text-indigo-500" /> YOUR CART</h1>
              {cart.length === 0 ? (
                <div className="text-center py-20 bg-zinc-900/50 rounded-3xl border border-white/5">
                  <p className="text-zinc-500 text-lg mb-6">Your cart is looking empty.</p>
                  <button onClick={() => setActiveTab('home')} className="bg-indigo-600 text-white px-8 py-3 font-bold rounded-full">Continue Shopping</button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                  <div className="md:col-span-2 space-y-6">
                    {cart.map((item, i) => (
                      <div key={i} className="flex gap-6 p-4 bg-zinc-900/50 rounded-2xl border border-white/5 items-center">
                        <img src={item.img} className="w-20 h-20 object-cover rounded-xl grayscale" />
                        <div className="flex-1"><h3 className="font-bold text-lg">{item.name}</h3><p className="text-indigo-400 font-bold">${item.price}</p></div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-zinc-900 rounded-3xl p-6 border border-white/5 h-fit">
                    <h3 className="font-bold text-xl mb-6">Summary</h3>
                    <div className="flex justify-between mb-4 text-zinc-400"><span>Subtotal</span><span>${total}</span></div>
                    <div className="flex justify-between mb-6 text-zinc-400"><span>Shipping</span><span>Free</span></div>
                    <div className="flex justify-between text-2xl font-black mb-8 pt-6 border-t border-white/10"><span>Total</span><span className="text-indigo-400">${total}</span></div>
                    <button className="w-full bg-white text-zinc-950 py-4 font-bold rounded-full flex justify-center items-center gap-2 hover:bg-indigo-50 hover:scale-105 transition-all">
                      <CreditCard className="w-5 h-5" /> CHECKOUT
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}"""

_FOOD = """import React,{useState} from 'react';
const restaurants=[{id:1,name:"Spice Garden",cuisine:"Indian",rating:4.8,time:"25 min",img:"https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400",items:[{n:"Butter Chicken",p:280},{n:"Paneer Tikka",p:220},{n:"Garlic Naan",p:60}]},{id:2,name:"Pizza Palace",cuisine:"Italian",rating:4.6,time:"30 min",img:"https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400",items:[{n:"Margherita",p:350},{n:"BBQ Chicken",p:420},{n:"Cheesy Burst",p:480}]},{id:3,name:"Dragon Wok",cuisine:"Chinese",rating:4.5,time:"20 min",img:"https://images.unsplash.com/photo-1563245372-f21724e3856d?w=400",items:[{n:"Fried Rice",p:180},{n:"Manchurian",p:200},{n:"Chow Mein",p:160}]}];
export default function App(){
  const[page,setPage]=useState('home');
  const[rest,setRest]=useState(null);
  const[cart,setCart]=useState([]);
  const add=(item)=>setCart(c=>[...c,item]);
  const total=cart.reduce((a,b)=>a+b.p,0);
  return(
    <div style={{fontFamily:'Inter,sans-serif',background:'#fff',minHeight:'100vh'}}>
      <nav style={{background:'#fc6011',padding:'16px 32px',display:'flex',justifyContent:'space-between',alignItems:'center',position:'sticky',top:0,zIndex:100}}>
        <span style={{fontSize:22,fontWeight:900,color:'#fff'}}>🍔 QuickBite</span>
        <button onClick={()=>setPage('cart')} style={{background:'#fff',color:'#fc6011',border:'none',padding:'8px 20px',borderRadius:20,fontWeight:700,cursor:'pointer'}}>Cart ({cart.length}) — ₹{total}</button>
      </nav>
      {page==='home'&&<>
        <div style={{background:'linear-gradient(135deg,#fc6011,#ff8c42)',padding:'60px 32px',textAlign:'center',color:'#fff'}}>
          <h1 style={{fontSize:48,fontWeight:900,margin:0}}>Hungry? We've Got You</h1>
          <p style={{fontSize:18,margin:'12px 0 32px',opacity:.9}}>Order from top restaurants near you</p>
          <input placeholder="Search for food or restaurant..." style={{width:'100%',maxWidth:500,padding:'14px 24px',borderRadius:30,border:'none',fontSize:16,outline:'none'}}/>
        </div>
        <div style={{maxWidth:1100,margin:'40px auto',padding:'0 24px'}}>
          <h2 style={{fontSize:24,fontWeight:700,marginBottom:24}}>Top Restaurants</h2>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:24}}>
            {restaurants.map(r=><div key={r.id} onClick={()=>{setRest(r);setPage('restaurant')}} style={{border:'1px solid #eee',borderRadius:16,overflow:'hidden',cursor:'pointer',boxShadow:'0 2px 8px rgba(0,0,0,.08)',transition:'transform .2s'}} onMouseEnter={e=>e.currentTarget.style.transform='translateY(-4px)'} onMouseLeave={e=>e.currentTarget.style.transform='none'}>
              <img src={r.img} style={{width:'100%',height:180,objectFit:'cover'}}/>
              <div style={{padding:16}}>
                <h3 style={{margin:'0 0 4px',fontSize:18,fontWeight:700}}>{r.name}</h3>
                <p style={{color:'#666',margin:'0 0 8px',fontSize:14}}>{r.cuisine}</p>
                <div style={{display:'flex',gap:16}}>
                  <span style={{color:'#4caf50',fontWeight:700}}>⭐ {r.rating}</span>
                  <span style={{color:'#888'}}>🕐 {r.time}</span>
                </div>
              </div>
            </div>)}
          </div>
        </div>
      </>}
      {page==='restaurant'&&rest&&<div style={{maxWidth:800,margin:'40px auto',padding:'0 24px'}}>
        <button onClick={()=>setPage('home')} style={{background:'#fc6011',color:'#fff',border:'none',padding:'8px 20px',borderRadius:20,cursor:'pointer',marginBottom:24,fontWeight:700}}>← Back</button>
        <img src={rest.img} style={{width:'100%',height:250,objectFit:'cover',borderRadius:16,marginBottom:24}}/>
        <h2 style={{fontSize:28,fontWeight:800,margin:'0 0 8px'}}>{rest.name}</h2>
        <p style={{color:'#666',marginBottom:24}}>{rest.cuisine} • ⭐ {rest.rating} • 🕐 {rest.time}</p>
        <h3 style={{fontSize:20,fontWeight:700,marginBottom:16}}>Menu</h3>
        {rest.items.map((item,i)=><div key={i} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'16px',border:'1px solid #eee',borderRadius:12,marginBottom:12}}>
          <div><p style={{margin:0,fontWeight:600,fontSize:16}}>{item.n}</p><p style={{margin:'4px 0 0',color:'#fc6011',fontWeight:700}}>₹{item.p}</p></div>
          <button onClick={()=>add(item)} style={{background:'#fc6011',color:'#fff',border:'none',padding:'8px 20px',borderRadius:20,cursor:'pointer',fontWeight:700}}>+ Add</button>
        </div>)}
      </div>}
      {page==='cart'&&<div style={{maxWidth:600,margin:'40px auto',padding:'0 24px'}}>
        <h2 style={{fontSize:28,fontWeight:700,marginBottom:24}}>Your Order</h2>
        {cart.length===0?<div style={{textAlign:'center',padding:80,color:'#999'}}><p style={{fontSize:48}}>🛒</p><p>No items yet</p><button onClick={()=>setPage('home')} style={{background:'#fc6011',color:'#fff',border:'none',padding:'12px 28px',borderRadius:20,cursor:'pointer',fontWeight:700}}>Browse Restaurants</button></div>:
        <>{cart.map((item,i)=><div key={i} style={{display:'flex',justifyContent:'space-between',padding:'12px 0',borderBottom:'1px solid #eee'}}><span>{item.n}</span><span style={{fontWeight:700,color:'#fc6011'}}>₹{item.p}</span></div>)}
        <div style={{marginTop:24,padding:20,background:'#fff8f4',borderRadius:12,border:'1px solid #fce4d6'}}>
          <div style={{display:'flex',justifyContent:'space-between',fontWeight:700,fontSize:18,marginBottom:16}}><span>Total</span><span style={{color:'#fc6011'}}>₹{total}</span></div>
          <button style={{width:'100%',background:'#fc6011',color:'#fff',border:'none',padding:14,borderRadius:10,fontSize:16,fontWeight:700,cursor:'pointer'}}>Place Order</button>
        </div></>}
      </div>}
    </div>
  );
}"""

_GENERIC = """import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, Users, Settings, Activity, Zap, ChevronRight, BarChart3, Globe } from 'lucide-react';

const STATS = [
  { label: "Total Revenue", value: "$124,500", icon: BarChart3, color: "text-emerald-400", bg: "bg-emerald-400/10" },
  { label: "Active Users", value: "24.5K", icon: Users, color: "text-blue-400", bg: "bg-blue-400/10" },
  { label: "Global Reach", value: "142", icon: Globe, color: "text-purple-400", bg: "bg-purple-400/10" },
  { label: "System Load", value: "98.2%", icon: Activity, color: "text-rose-400", bg: "bg-rose-400/10" }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30 overflow-hidden">
      {/* Sidebar */}
      <motion.div initial={{ x: -300 }} animate={{ x: 0 }} className="w-72 bg-zinc-900/50 border-r border-white/5 flex flex-col backdrop-blur-xl z-20 relative">
        <div className="h-20 flex items-center px-8 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center rounded-xl shadow-lg shadow-indigo-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-black tracking-tight">PULSE<span className="text-indigo-400">.</span></span>
          </div>
        </div>
        <div className="flex-1 py-8 px-4 space-y-2">
          {[
            { id: 'dashboard', icon: LayoutDashboard, label: 'Overview' },
            { id: 'users', icon: Users, label: 'Customers' },
            { id: 'analytics', icon: BarChart3, label: 'Analytics' },
            { id: 'settings', icon: Settings, label: 'Settings' }
          ].map(nav => (
            <button key={nav.id} onClick={() => setActiveTab(nav.id)} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${activeTab === nav.id ? 'bg-indigo-500/10 text-indigo-400 font-bold' : 'text-zinc-400 hover:bg-white/5 hover:text-white'}`}>
              <nav.icon className="w-5 h-5" /> {nav.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative overflow-y-auto">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[120px] pointer-events-none translate-y-1/2 -translate-x-1/2" />
        
        <header className="h-20 border-b border-white/5 flex items-center justify-between px-10 relative z-10 backdrop-blur-md bg-zinc-950/50">
          <h2 className="text-2xl font-black tracking-tight capitalize">{activeTab}</h2>
          <div className="w-10 h-10 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center font-bold">A</div>
        </header>

        <main className="flex-1 p-10 relative z-10">
          {activeTab === 'dashboard' && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {STATS.map((stat, i) => (
                  <motion.div key={i} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.1 }} className="p-6 bg-zinc-900/50 rounded-3xl border border-white/5 relative overflow-hidden group hover:border-white/10 transition-colors">
                    <div className={`w-12 h-12 rounded-2xl ${stat.bg} ${stat.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                      <stat.icon className="w-6 h-6" />
                    </div>
                    <p className="text-zinc-500 font-medium mb-1">{stat.label}</p>
                    <h3 className="text-3xl font-black tracking-tighter text-white">{stat.value}</h3>
                  </motion.div>
                ))}
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 p-8 bg-zinc-900/50 rounded-3xl border border-white/5 min-h-[400px] flex flex-col justify-center items-center">
                   <Activity className="w-16 h-16 text-zinc-800 mb-4" />
                   <p className="text-zinc-500 font-medium">Real-time chart data will appear here.</p>
                </div>
                <div className="p-8 bg-zinc-900/50 rounded-3xl border border-white/5">
                  <h3 className="font-bold text-lg mb-6">Recent Activity</h3>
                  <div className="space-y-6">
                    {[1,2,3,4].map(i => (
                      <div key={i} className="flex gap-4 items-start">
                        <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2 shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                        <div>
                          <p className="text-sm font-medium text-zinc-200">System update completed</p>
                          <p className="text-xs text-zinc-500">{i * 12} mins ago</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab !== 'dashboard' && (
             <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[60vh] flex flex-col items-center justify-center text-center">
                <div className="w-20 h-20 bg-zinc-900 rounded-3xl border border-white/5 flex items-center justify-center mb-6">
                  <Settings className="w-8 h-8 text-zinc-600" />
                </div>
                <h2 className="text-3xl font-black tracking-tighter mb-4 capitalize">{activeTab} Module</h2>
                <p className="text-zinc-500 max-w-md">This module is currently being provisioned. Connected data will appear once the APIs are fully integrated.</p>
             </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}"""

_BACKEND_ECOMMERCE = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Shop API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
products = [
    {"id":1,"name":"Gold Ring 22K","price":24999,"category":"rings","stock":15},
    {"id":2,"name":"Diamond Necklace","price":89999,"category":"necklaces","stock":8},
    {"id":3,"name":"Pearl Bracelet","price":12999,"category":"bracelets","stock":22},
]
orders = []
@app.get("/api/health")
def health(): return {"status":"OK"}
@app.get("/api/products")
def get_products(): return products
@app.post("/api/orders")
def create_order(order: dict): orders.append(order); return {"id":len(orders),"status":"confirmed"}
@app.get("/api/orders")
def get_orders(): return orders
"""

_BACKEND_FOOD = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Food API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
restaurants = [{"id":1,"name":"Spice Garden","cuisine":"Indian","rating":4.8},{"id":2,"name":"Pizza Palace","cuisine":"Italian","rating":4.6}]
orders = []
@app.get("/api/health")
def health(): return {"status":"OK"}
@app.get("/api/restaurants")
def get_restaurants(): return restaurants
@app.post("/api/orders")
def place_order(order: dict): orders.append(order); return {"id":len(orders),"status":"placed","eta":"25 min"}
@app.get("/api/orders")
def get_orders(): return orders
"""

_BACKEND_GENERIC = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="App API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
items = []
@app.get("/api/health")
def health(): return {"status":"OK"}
@app.get("/api/items")
def list_items(): return items
@app.post("/api/items")
def create_item(item: dict): items.append(item); return {"id":len(items)}
@app.post("/api/contact")
def contact(data: dict): return {"received":True}
"""


_FITNESS = """import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, Activity, Calendar, Users, ChevronRight, Zap } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-orange-500/30 overflow-hidden">
      <nav className="fixed w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center rounded-xl shadow-lg shadow-orange-500/20">
              <Dumbbell className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-black tracking-tight">IRON<span className="text-orange-500">CORE</span></span>
          </div>
          <div className="hidden md:flex items-center gap-8 font-medium text-sm">
            {['Home', 'Classes', 'Trainers', 'Pricing'].map(item => (
              <button key={item} onClick={() => setActiveTab(item.toLowerCase())} className={`transition-colors ${activeTab === item.toLowerCase() ? 'text-orange-500' : 'text-zinc-400 hover:text-white'}`}>{item}</button>
            ))}
          </div>
          <button className="px-6 py-2.5 bg-white text-black font-bold rounded-full hover:scale-105 transition-transform">Join Now</button>
        </div>
      </nav>

      <main className="pt-20">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div key="home" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="relative">
              <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-orange-600/20 rounded-full blur-[120px] pointer-events-none" />
              <div className="max-w-7xl mx-auto px-6 pt-32 pb-24 text-center relative z-10">
                <motion.h1 initial={{y:20, opacity:0}} animate={{y:0, opacity:1}} className="text-6xl md:text-8xl font-black tracking-tighter mb-8">
                  FORGE YOUR <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-red-600">LEGACY</span>
                </motion.h1>
                <motion.p initial={{y:20, opacity:0}} animate={{y:0, opacity:1}} transition={{delay:0.1}} className="text-xl text-zinc-400 mb-12 max-w-2xl mx-auto">
                  Elite training facility with state-of-the-art equipment and world-class trainers. Push beyond your limits.
                </motion.p>
                <motion.div initial={{y:20, opacity:0}} animate={{y:0, opacity:1}} transition={{delay:0.2}} className="flex justify-center gap-4">
                  <button className="px-8 py-4 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-full transition-colors flex items-center gap-2">
                    Start Free Trial <ChevronRight className="w-5 h-5"/>
                  </button>
                </motion.div>
              </div>

              <div className="max-w-7xl mx-auto px-6 py-24 grid md:grid-cols-3 gap-8 relative z-10">
                {[
                  { title: "Elite Equipment", icon: Zap, desc: "Latest machines and free weights." },
                  { title: "Expert Trainers", icon: Users, desc: "Guidance from fitness professionals." },
                  { title: "Daily Classes", icon: Activity, desc: "HIIT, Yoga, CrossFit and more." }
                ].map((feature, i) => (
                  <motion.div key={i} initial={{opacity:0, y:20}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{delay:i*0.1}} className="p-8 rounded-3xl bg-zinc-900/50 border border-white/5 hover:border-orange-500/50 transition-colors group">
                    <feature.icon className="w-12 h-12 text-orange-500 mb-6 group-hover:scale-110 transition-transform" />
                    <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
                    <p className="text-zinc-400">{feature.desc}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}"""

def get_fallback_app(domain: str, title: str) -> dict:
    """Return guaranteed real React app + backend for given domain."""
    if domain == "ecommerce":
        return {"app": _ECOMMERCE, "backend": _BACKEND_ECOMMERCE}
    elif domain == "food_delivery":
        return {"app": _FOOD, "backend": _BACKEND_FOOD}
    elif domain == "fitness":
        return {"app": _FITNESS, "backend": _BACKEND_GENERIC}
    else:
        return {"app": _GENERIC, "backend": _BACKEND_GENERIC}
