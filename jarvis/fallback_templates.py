"""Hardcoded fallback apps — deployed when AI generation fails."""

_ECOMMERCE = """import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingBag, Star, Zap, ArrowRight, X, CreditCard, CheckCircle2, Package, Eye } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [checkingOut, setCheckingOut] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  useEffect(() => {
    fetch('/api/products')
      .then(r => r.json())
      .then(setProducts)
      .catch(e => console.error("Error fetching products:", e));
      
    fetch('/api/orders')
      .then(r => r.json())
      .then(setOrders)
      .catch(e => console.error("Error fetching orders:", e));
  }, []);

  const addToCart = (p) => setCart(c => [...c, p]);
  
  const removeFromCart = (id) => {
    const idx = cart.findIndex(item => item.id === id);
    if (idx > -1) {
      const newCart = [...cart];
      newCart.splice(idx, 1);
      setCart(newCart);
    }
  };

  const total = cart.reduce((a, b) => a + b.price, 0);

  const handleCheckout = () => {
    if (cart.length === 0) return;
    setCheckingOut(true);
    fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: cart, total: total })
    })
    .then(r => r.json())
    .then(res => {
      setCheckingOut(false);
      setOrderSuccess(true);
      setCart([]);
      fetch('/api/orders').then(r => r.json()).then(setOrders).catch(() => {});
    })
    .catch(() => setCheckingOut(false));
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30 overflow-x-hidden">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <button onClick={() => { setActiveTab('home'); setOrderSuccess(false); }} className="flex items-center gap-2">
            <div className="w-10 h-10 bg-indigo-600 flex items-center justify-center rounded-lg rotate-3">
              <Zap className="w-6 h-6 text-white -rotate-3" />
            </div>
            <span className="text-2xl font-black tracking-tighter text-white uppercase">NEXUS<span className="text-indigo-500">.</span></span>
          </button>
          <div className="flex items-center gap-6">
            <button onClick={() => { setActiveTab('shop'); setOrderSuccess(false); }} className="text-zinc-400 hover:text-white font-medium text-sm">Shop</button>
            <button onClick={() => { setActiveTab('orders'); setOrderSuccess(false); }} className="text-zinc-400 hover:text-white font-medium text-sm">My Orders</button>
            <button onClick={() => { setActiveTab('cart'); setOrderSuccess(false); }} className="flex items-center gap-2 bg-white/5 hover:bg-white/10 px-4 py-2 rounded-full transition-colors border border-white/5">
              <ShoppingBag className="w-5 h-5 text-indigo-400" />
              <span className="font-bold">{cart.length}</span>
            </button>
          </div>
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
                    <button onClick={() => setActiveTab('shop')} className="bg-white text-zinc-950 px-8 py-4 font-black tracking-wider hover:scale-105 transition-transform flex items-center gap-2 rounded-full">
                      SHOP NOW <ArrowRight className="w-5 h-5" />
                    </button>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'shop' && (
            <motion.div key="shop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="py-24 max-w-7xl mx-auto px-6">
              <h2 className="text-4xl font-black tracking-tight mb-12">FEATURED DROPS</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {products.map((p, i) => (
                  <motion.div key={p.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} className="group cursor-pointer">
                    <div className="relative h-80 bg-zinc-900 rounded-2xl overflow-hidden mb-4">
                      <img src={p.img} alt={p.name} className="w-full h-full object-cover grayscale transition-all duration-500 group-hover:grayscale-0 group-hover:scale-110" />
                      <div className="absolute top-4 left-4 bg-zinc-950/80 backdrop-blur text-white px-3 py-1 text-xs font-bold rounded-full border border-white/10">{p.tag}</div>
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                         <button onClick={(e) => { e.stopPropagation(); addToCart(p); }} className="bg-indigo-600 text-white px-6 py-3 font-bold rounded-full hover:bg-indigo-500 hover:scale-105 transition-all">ADD TO CART</button>
                      </div>
                    </div>
                    <h3 className="text-lg font-bold">{p.name}</h3>
                    <p className="text-zinc-500 text-sm mb-1">{p.desc}</p>
                    <p className="text-indigo-400 font-bold">${p.price}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'cart' && (
            <motion.div key="cart" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="min-h-screen py-20 px-6 max-w-4xl mx-auto">
              <h1 className="text-4xl font-black tracking-tighter mb-12 flex items-center gap-4"><ShoppingBag className="w-8 h-8 text-indigo-500" /> YOUR CART</h1>
              {orderSuccess ? (
                <div className="text-center py-20 bg-zinc-900/50 rounded-3xl border border-white/5">
                  <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto mb-6" />
                  <h2 className="text-2xl font-black mb-2">Order Confirmed!</h2>
                  <p className="text-zinc-400 mb-6">Your order is being processed and will ship soon.</p>
                  <button onClick={() => { setActiveTab('orders'); setOrderSuccess(false); }} className="bg-indigo-600 text-white px-8 py-3 font-bold rounded-full">Track Orders</button>
                </div>
              ) : cart.length === 0 ? (
                <div className="text-center py-20 bg-zinc-900/50 rounded-3xl border border-white/5">
                  <p className="text-zinc-500 text-lg mb-6">Your cart is looking empty.</p>
                  <button onClick={() => setActiveTab('shop')} className="bg-indigo-600 text-white px-8 py-3 font-bold rounded-full">Go to Shop</button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                  <div className="md:col-span-2 space-y-6">
                    {cart.map((item, i) => (
                      <div key={i} className="flex gap-6 p-4 bg-zinc-900/50 rounded-2xl border border-white/5 items-center justify-between">
                        <div className="flex gap-6 items-center">
                          <img src={item.img} className="w-20 h-20 object-cover rounded-xl grayscale" />
                          <div>
                            <h3 className="font-bold text-lg">{item.name}</h3>
                            <p className="text-indigo-400 font-bold">${item.price}</p>
                          </div>
                        </div>
                        <button onClick={() => removeFromCart(item.id)} className="text-zinc-500 hover:text-rose-500 p-2"><X className="w-5 h-5" /></button>
                      </div>
                    ))}
                  </div>
                  <div className="bg-zinc-900 rounded-3xl p-6 border border-white/5 h-fit">
                    <h3 className="font-bold text-xl mb-6">Summary</h3>
                    <div className="flex justify-between mb-4 text-zinc-400"><span>Subtotal</span><span>${total}</span></div>
                    <div className="flex justify-between mb-6 text-zinc-400"><span>Shipping</span><span>Free</span></div>
                    <div className="flex justify-between text-2xl font-black mb-8 pt-6 border-t border-white/10"><span>Total</span><span className="text-indigo-400">${total}</span></div>
                    <button onClick={handleCheckout} disabled={checkingOut} className="w-full bg-white text-zinc-950 py-4 font-bold rounded-full flex justify-center items-center gap-2 hover:bg-indigo-50 hover:scale-105 transition-all">
                      <CreditCard className="w-5 h-5" /> {checkingOut ? "PROCESSING..." : "CHECKOUT"}
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'orders' && (
            <motion.div key="orders" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="min-h-screen py-20 px-6 max-w-4xl mx-auto">
              <h1 className="text-4xl font-black tracking-tighter mb-12 flex items-center gap-4"><Package className="w-8 h-8 text-indigo-500" /> ORDER HISTORY</h1>
              {orders.length === 0 ? (
                <div className="text-center py-20 bg-zinc-900/50 rounded-3xl border border-white/5">
                  <p className="text-zinc-500">No orders found.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {orders.map((ord, idx) => (
                    <div key={idx} className="p-6 bg-zinc-900/50 border border-white/5 rounded-2xl">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-bold text-lg">Order #{ord.id}</h3>
                          <p className="text-sm text-zinc-500">Status: <span className="text-indigo-400 font-bold">{ord.status}</span></p>
                        </div>
                        <span className="text-xl font-black text-indigo-400">${ord.total}</span>
                      </div>
                      <div className="space-y-2 border-t border-white/5 pt-4">
                        {ord.items.map((item, i) => (
                          <div key={i} className="flex justify-between text-sm text-zinc-400">
                            <span>{item.name}</span>
                            <span>${item.price}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
"""

_FOOD = """import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingBag, Star, Clock, CheckCircle2, Utensils, ArrowLeft, Heart, Package } from 'lucide-react';

export default function App() {
  const [page, setPage] = useState('home');
  const [restaurants, setRestaurants] = useState([]);
  const [selectedRest, setSelectedRest] = useState(null);
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [placed, setPlaced] = useState(false);

  useEffect(() => {
    fetch('/api/restaurants')
      .then(r => r.json())
      .then(setRestaurants)
      .catch(e => console.error("Error fetching restaurants:", e));
      
    fetch('/api/orders')
      .then(r => r.json())
      .then(setOrders)
      .catch(e => console.error("Error fetching orders:", e));
  }, []);

  const addToCart = (item) => setCart(c => [...c, item]);
  const total = cart.reduce((a, b) => a + b.price, 0);

  const placeOrder = () => {
    if (cart.length === 0) return;
    fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: cart, total: total, restaurant: selectedRest?.name || "QuickBite" })
    })
    .then(r => r.json())
    .then(res => {
      setPlaced(true);
      setCart([]);
      fetch('/api/orders').then(r => r.json()).then(setOrders).catch(() => {});
    });
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-orange-500/30 overflow-x-hidden">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <button onClick={() => { setPage('home'); setSelectedRest(null); setPlaced(false); }} className="flex items-center gap-2">
            <div className="w-10 h-10 bg-orange-600 rounded-xl flex items-center justify-center">
              <Utensils className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-black tracking-tight text-white uppercase">Quick<span className="text-orange-500">Bite</span></span>
          </button>
          <div className="flex items-center gap-6">
            <button onClick={() => { setPage('orders'); setPlaced(false); }} className="text-zinc-400 hover:text-white font-medium text-sm">Track Orders</button>
            <button onClick={() => { setPage('cart'); setPlaced(false); }} className="bg-white/5 hover:bg-white/10 px-4 py-2 rounded-full border border-white/5 flex items-center gap-2 transition-all">
              <ShoppingBag className="w-4 h-4 text-orange-500" />
              <span className="font-bold text-sm">{cart.length}</span>
            </button>
          </div>
        </div>
      </nav>

      <main className="pt-20">
        <AnimatePresence mode="wait">
          {page === 'home' && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="relative bg-gradient-to-b from-orange-950/30 to-zinc-950 py-24 text-center">
                <h1 className="text-5xl md:text-7xl font-black tracking-tighter mb-6">
                  CRAVE IT. <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-500">WE GET IT.</span>
                </h1>
                <p className="text-zinc-400 text-lg mb-8 max-w-xl mx-auto">Fresh, hot food delivered directly from the finest local restaurants.</p>
              </div>

              <div className="max-w-7xl mx-auto px-6 py-12">
                <h2 className="text-2xl font-black mb-8">Popular Restaurants</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                  {restaurants.map(r => (
                    <motion.div key={r.id} onClick={() => { setSelectedRest(r); setPage('menu'); }} whileHover={{ y: -6 }} className="bg-zinc-900/50 border border-white/5 rounded-3xl overflow-hidden cursor-pointer hover:border-orange-500/30 transition-all">
                      <img src={r.img} className="w-full h-48 object-cover grayscale hover:grayscale-0 transition-all duration-500" alt={r.name} />
                      <div className="p-6">
                        <h3 className="text-xl font-bold mb-2">{r.name}</h3>
                        <p className="text-zinc-400 text-sm mb-4">{r.cuisine}</p>
                        <div className="flex gap-4 text-sm font-semibold">
                          <span className="text-emerald-400 flex items-center gap-1"><Star className="w-4 h-4 fill-emerald-400" /> {r.rating}</span>
                          <span className="text-zinc-500 flex items-center gap-1"><Clock className="w-4 h-4" /> {r.time}</span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {page === 'menu' && selectedRest && (
            <motion.div key="menu" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="max-w-3xl mx-auto px-6 py-12">
              <button onClick={() => { setPage('home'); setSelectedRest(null); }} className="flex items-center gap-2 text-zinc-400 hover:text-white mb-8 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Restaurants
              </button>
              <img src={selectedRest.img} className="w-full h-64 object-cover rounded-3xl mb-8" alt={selectedRest.name} />
              <h1 className="text-4xl font-black tracking-tight mb-2">{selectedRest.name}</h1>
              <p className="text-zinc-400 mb-8">{selectedRest.cuisine} • ⭐ {selectedRest.rating} • 🕐 {selectedRest.time}</p>

              <h2 className="text-2xl font-black mb-6">Menu</h2>
              <div className="space-y-4">
                {selectedRest.items?.map((item, i) => (
                  <div key={i} className="flex justify-between items-center p-6 bg-zinc-900/30 border border-white/5 rounded-2xl">
                    <div>
                      <h3 className="font-bold text-lg">{item.name}</h3>
                      <p className="text-orange-500 font-bold mt-1">₹{item.price}</p>
                    </div>
                    <button onClick={() => addToCart(item)} className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-full font-bold transition-all hover:scale-105">+ Add</button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {page === 'cart' && (
            <motion.div key="cart" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-xl mx-auto px-6 py-12">
              <h1 className="text-3xl font-black mb-8">Your Cart</h1>
              {placed ? (
                <div className="p-8 bg-emerald-500/10 border border-emerald-500/30 rounded-3xl text-center">
                  <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
                  <h2 className="text-xl font-bold text-white mb-2">Order Confirmed!</h2>
                  <p className="text-zinc-400 text-sm mb-6">Your fresh meal is being prepared and will arrive soon.</p>
                  <button onClick={() => { setPage('orders'); setPlaced(false); }} className="bg-emerald-500 text-black px-6 py-2.5 rounded-full font-bold">Track Order</button>
                </div>
              ) : cart.length === 0 ? (
                <div className="text-center py-16 bg-zinc-900/30 border border-white/5 rounded-3xl">
                  <p className="text-zinc-500 mb-6">Your cart is empty.</p>
                  <button onClick={() => setPage('home')} className="bg-orange-500 text-white px-6 py-2.5 rounded-full font-bold">Find Food</button>
                </div>
              ) : (
                <div className="space-y-6">
                  {cart.map((item, i) => (
                    <div key={i} className="flex justify-between items-center py-4 border-b border-white/5">
                      <span>{item.name}</span>
                      <span className="font-bold text-orange-500">₹{item.price}</span>
                    </div>
                  ))}
                  <div className="pt-6">
                    <div className="flex justify-between text-xl font-black mb-6">
                      <span>Total</span>
                      <span className="text-orange-500">₹{total}</span>
                    </div>
                    <button onClick={placeOrder} className="w-full bg-orange-500 hover:bg-orange-600 text-white py-4 rounded-full font-bold transition-transform hover:scale-[1.02]">
                      Place Order
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {page === 'orders' && (
            <motion.div key="orders" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-2xl mx-auto px-6 py-12">
              <h1 className="text-3xl font-black mb-8">Active Orders</h1>
              {orders.length === 0 ? (
                <div className="text-center py-16 bg-zinc-900/30 border border-white/5 rounded-3xl">
                  <p className="text-zinc-500">No active orders found.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {orders.map((ord, idx) => (
                    <div key={idx} className="p-6 bg-zinc-900/50 border border-white/5 rounded-3xl">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-bold text-lg">Order #{ord.id}</h3>
                          <p className="text-sm text-zinc-500">From: {ord.restaurant}</p>
                        </div>
                        <span className="px-3 py-1 bg-orange-500/10 border border-orange-500/30 text-orange-400 text-xs font-bold rounded-full">{ord.status}</span>
                      </div>
                      <div className="space-y-2">
                        {ord.items.map((item, i) => (
                          <div key={i} className="flex justify-between text-sm text-zinc-400">
                            <span>{item.name}</span>
                            <span>₹{item.price}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 pt-4 border-t border-white/5 flex justify-between font-bold text-white">
                        <span>Total Paid</span>
                        <span>₹{ord.total}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
"""

_GENERIC = """import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, Users, Settings, Activity, Zap, BarChart3, Globe } from 'lucide-react';

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
}
"""

_BACKEND_ECOMMERCE = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Shop API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

products = [
    {"id": 1, "name": "Neon Chronograph", "price": 299, "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80", "tag": "NEW", "desc": "Sleek modern tactical chronograph with neon backlighting."},
    {"id": 2, "name": "Urban Backpack", "price": 129, "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&q=80", "tag": "BESTSELLER", "desc": "Waterproof multi-compartment pack designed for the digital nomad."},
    {"id": 3, "name": "Aero Sneakers", "price": 189, "img": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80", "tag": "TRENDING", "desc": "Ultra-lightweight mesh runners with responsive foam."},
    {"id": 4, "name": "Minimalist Shades", "price": 89, "img": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&q=80", "tag": "LIMITED", "desc": "Polarized acetate frames providing maximum UV protection."}
]

orders = []

class OrderItem(BaseModel):
    id: int
    name: str
    price: float

class OrderRequest(BaseModel):
    items: List[OrderItem]
    total: float

@app.get("/api/health")
def health(): return {"status":"OK"}

@app.get("/api/products")
def get_products(): return products

@app.post("/api/orders")
def create_order(order: OrderRequest):
    new_order = {
        "id": len(orders) + 1,
        "items": [item.dict() for item in order.items],
        "total": order.total,
        "status": "Shipped"
    }
    orders.append(new_order)
    return {"id": new_order["id"], "status": "confirmed"}

@app.get("/api/orders")
def get_orders(): return orders
"""

_BACKEND_FOOD = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Food API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

restaurants = [
    {
        "id": 1,
        "name": "Spice Garden",
        "cuisine": "Indian",
        "rating": 4.8,
        "time": "25 min",
        "img": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&q=80",
        "items": [
            {"name": "Butter Chicken", "price": 280},
            {"name": "Paneer Tikka", "price": 220},
            {"name": "Garlic Naan", "price": 60}
        ]
    },
    {
        "id": 2,
        "name": "Pizza Palace",
        "cuisine": "Italian",
        "rating": 4.6,
        "time": "30 min",
        "img": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
        "items": [
            {"name": "Margherita", "price": 350},
            {"name": "BBQ Chicken", "price": 420},
            {"name": "Cheesy Burst", "price": 480}
        ]
    },
    {
        "id": 3,
        "name": "Dragon Wok",
        "cuisine": "Chinese",
        "rating": 4.5,
        "time": "20 min",
        "img": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=800&q=80",
        "items": [
            {"name": "Fried Rice", "price": 180},
            {"name": "Manchurian", "price": 200},
            {"name": "Chow Mein", "price": 160}
        ]
    }
]

orders = []

class FoodItem(BaseModel):
    name: str
    price: float

class OrderRequest(BaseModel):
    items: List[FoodItem]
    total: float
    restaurant: str

@app.get("/api/health")
def health(): return {"status":"OK"}

@app.get("/api/restaurants")
def get_restaurants(): return restaurants

@app.post("/api/orders")
def place_order(order: OrderRequest):
    new_order = {
        "id": len(orders) + 1,
        "items": [item.dict() for item in order.items],
        "total": order.total,
        "restaurant": order.restaurant,
        "status": "Out for Delivery"
    }
    orders.append(new_order)
    return {"id": new_order["id"], "status": "placed", "eta": "25 min"}

@app.get("/api/orders")
def get_orders(): return orders
"""

_BACKEND_GENERIC = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

_BACKEND_FITNESS = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="IronCore Fitness API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

classes = [
    {"name": "Power Lifting", "time": "Mon/Wed 8:00 AM", "trainer": "Marcus Webb", "color": "from-orange-500 to-red-600"},
    {"name": "Cardio Blast", "time": "Tue/Thu 9:00 AM", "trainer": "Sarah Chen", "color": "from-blue-500 to-indigo-600"},
    {"name": "HIIT Intensity", "time": "Mon/Fri 6:00 PM", "trainer": "Alex Rivera", "color": "from-purple-500 to-pink-600"},
    {"name": "Yoga Flow", "time": "Daily 7:00 AM", "trainer": "Priya Nair", "color": "from-emerald-500 to-teal-600"},
    {"name": "CrossFit Core", "time": "Wed/Sat 10:00 AM", "trainer": "Jordan Lee", "color": "from-yellow-500 to-amber-600"}
]

trainers = [
    {"name": "Marcus Webb", "role": "Strength Specialist", "exp": "8 Years Exp", "bio": "Helps you hit new Personal Records safely.", "img": "https://images.unsplash.com/photo-1567013127542-490d757e51fc?w=400&q=80"},
    {"name": "Sarah Chen", "role": "Cardio & Endurance", "exp": "6 Years Exp", "bio": "High energy classes designed to burn calories.", "img": "https://images.unsplash.com/photo-1548690312-e3b507d8c110?w=400&q=80"},
    {"name": "Jordan Lee", "role": "CrossFit Coach", "exp": "5 Years Exp", "bio": "Functional fitness routines for everyday athletes.", "img": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&q=80"}
]

pricing = [
    {"name": "Basic", "price": "49", "features": ["Access to Gym Floor", "Locker Room access", "1 Free Trainer session"]},
    {"name": "Premium", "price": "99", "features": ["Unlimited Classes", "All Gym Floor access", "Personalized workout plan", "5 Free Trainer sessions"], "popular": True},
    {"name": "Elite", "price": "199", "features": ["24/7 Access", "Private Locker", "Dedicated Personal Trainer", "Custom diet & nutrition plans", "Unlimited classes & spa"]}
]

class EnrollForm(BaseModel):
    name: str
    email: str
    plan: str

@app.get("/api/health")
def health(): return {"status":"OK"}

@app.get("/api/classes")
def get_classes(): return classes

@app.get("/api/trainers")
def get_trainers(): return trainers

@app.get("/api/pricing")
def get_pricing(): return pricing

@app.post("/api/enroll")
def enroll(data: EnrollForm): return {"status": "success", "message": f"Successfully enrolled in {data.plan} plan!"}
"""

_FITNESS = """import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, Activity, Calendar, Users, ChevronRight, Zap, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [classes, setClasses] = useState([]);
  const [trainers, setTrainers] = useState([]);
  const [pricing, setPricing] = useState([]);
  const [enrolled, setEnrolled] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', plan: 'Premium' });

  useEffect(() => {
    fetch('/api/classes').then(r => r.json()).then(setClasses).catch(() => {});
    fetch('/api/trainers').then(r => r.json()).then(setTrainers).catch(() => {});
    fetch('/api/pricing').then(r => r.json()).then(setPricing).catch(() => {});
  }, []);

  const handleEnroll = (e) => {
    e.preventDefault();
    fetch('/api/enroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form)
    }).then(r => r.json()).then(() => {
      setEnrolled(true);
    });
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-orange-500/30 overflow-x-hidden">
      <nav className="fixed w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <button onClick={() => setActiveTab('home')} className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center rounded-xl shadow-lg shadow-orange-500/20">
              <Dumbbell className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-black tracking-tight">IRON<span className="text-orange-500">CORE</span></span>
          </button>
          <div className="hidden md:flex items-center gap-8 font-medium text-sm">
            {['Home', 'Classes', 'Trainers', 'Pricing'].map(item => (
              <button key={item} onClick={() => setActiveTab(item.toLowerCase())} className={`transition-colors ${activeTab === item.toLowerCase() ? 'text-orange-500' : 'text-zinc-400 hover:text-white'}`}>{item}</button>
            ))}
          </div>
          <button onClick={() => setActiveTab('enroll')} className="px-6 py-2.5 bg-white text-black font-bold rounded-full hover:scale-105 transition-transform">Join Now</button>
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
                  <button onClick={() => setActiveTab('classes')} className="px-8 py-4 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-full transition-colors flex items-center gap-2">
                    Start Free Trial <ChevronRight className="w-5 h-5"/>
                  </button>
                </motion.div>
              </div>

              <div className="max-w-7xl mx-auto px-6 py-24 grid md:grid-cols-3 gap-8 relative z-10">
                {[
                  { title: "Elite Equipment", desc: "Latest machines and free weights." },
                  { title: "Expert Trainers", desc: "Guidance from fitness professionals." },
                  { title: "Daily Classes", desc: "HIIT, Yoga, CrossFit and more." }
                ].map((feature, i) => (
                  <motion.div key={i} initial={{opacity:0, y:20}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{delay:i*0.1}} className="p-8 rounded-3xl bg-zinc-900/50 border border-white/5 hover:border-orange-500/50 transition-colors group">
                    <Zap className="w-12 h-12 text-orange-500 mb-6 group-hover:scale-110 transition-transform" />
                    <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
                    <p className="text-zinc-400">{feature.desc}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'classes' && (
            <motion.div key="classes" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0}} className="max-w-7xl mx-auto px-6 py-24">
              <h2 className="text-4xl font-black mb-10 text-center">OUR CLASSES</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                {classes.map((c, i) => (
                  <div key={i} className="p-8 rounded-3xl bg-zinc-900/50 border border-white/5 relative overflow-hidden group hover:border-orange-500/50 transition-colors">
                    <div className={`absolute top-0 left-0 w-2 h-full bg-gradient-to-b ${c.color}`} />
                    <h3 className="text-2xl font-bold mb-4">{c.name}</h3>
                    <p className="text-zinc-400 mb-2">Schedule: {c.time}</p>
                    <p className="text-orange-500 font-medium">Trainer: {c.trainer}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'trainers' && (
            <motion.div key="trainers" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0}} className="max-w-7xl mx-auto px-6 py-24">
              <h2 className="text-4xl font-black mb-10 text-center">EXPERT INSTRUCTORS</h2>
              <div className="grid md:grid-cols-3 gap-8">
                {trainers.map((t, i) => (
                  <div key={i} className="rounded-3xl bg-zinc-900/50 border border-white/5 overflow-hidden hover:border-orange-500/50 transition-colors">
                    <img src={t.img} alt={t.name} className="w-full h-64 object-cover grayscale hover:grayscale-0 transition-all duration-300" />
                    <div className="p-6">
                      <h3 className="text-xl font-bold">{t.name}</h3>
                      <p className="text-orange-500 text-sm font-semibold mb-3">{t.role} • {t.exp}</p>
                      <p className="text-zinc-400 text-sm">{t.bio}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'pricing' && (
            <motion.div key="pricing" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0}} className="max-w-7xl mx-auto px-6 py-24">
              <h2 className="text-4xl font-black mb-10 text-center">MEMBERSHIP PLANS</h2>
              <div className="grid md:grid-cols-3 gap-8">
                {pricing.map((p, i) => (
                  <div key={i} className={`p-8 rounded-3xl bg-zinc-900/50 border ${p.popular ? 'border-orange-500 shadow-lg shadow-orange-500/10' : 'border-white/5'} relative overflow-hidden flex flex-col justify-between`}>
                    {p.popular && <div className="absolute top-4 right-4 bg-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</div>}
                    <div>
                      <h3 className="text-2xl font-bold mb-2">{p.name}</h3>
                      <div className="flex items-baseline gap-1 mb-6">
                        <span className="text-4xl font-black">${p.price}</span>
                        <span className="text-zinc-500 text-sm">/month</span>
                      </div>
                      <ul className="space-y-3 mb-8">
                        {p.features.map((f, j) => (
                          <li key={j} className="text-zinc-400 text-sm flex items-center gap-2">✓ {f}</li>
                        ))}
                      </ul>
                    </div>
                    <button onClick={() => { setForm(f => ({ ...f, plan: p.name })); setActiveTab('enroll'); }} className={`w-full py-3 font-bold rounded-full transition-transform hover:scale-105 ${p.popular ? 'bg-orange-500 text-white' : 'bg-white text-zinc-950'}`}>Select Plan</button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'enroll' && (
            <motion.div key="enroll" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0}} className="max-w-md mx-auto px-6 py-24">
              <h2 className="text-4xl font-black mb-8 text-center">JOIN THE IRONCORE</h2>
              {enrolled ? (
                <div className="p-6 rounded-2xl bg-orange-500/10 border border-orange-500/30 flex gap-3 items-center text-orange-400">
                  <CheckCircle2 /> Successfully registered! Welcome to the squad.
                </div>
              ) : (
                <form onSubmit={handleEnroll} className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold mb-2 text-zinc-400">Name</label>
                    <input required className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10 outline-none focus:border-orange-500 text-zinc-200" placeholder="Your Name" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
                  </div>
                  <div>
                    <label className="block text-sm font-bold mb-2 text-zinc-400">Email Address</label>
                    <input required type="email" className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10 outline-none focus:border-orange-500 text-zinc-200" placeholder="you@example.com" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} />
                  </div>
                  <div>
                    <label className="block text-sm font-bold mb-2 text-zinc-400">Select Plan</label>
                    <select className="w-full p-4 rounded-xl bg-zinc-900 border border-white/10 outline-none focus:border-orange-500 text-zinc-300" value={form.plan} onChange={e => setForm(f => ({...f, plan: e.target.value}))}>
                      <option value="Basic">Basic Plan ($49/mo)</option>
                      <option value="Premium">Premium Plan ($99/mo)</option>
                      <option value="Elite">Elite Plan ($199/mo)</option>
                    </select>
                  </div>
                  <button type="submit" className="w-full py-4 bg-orange-500 hover:bg-orange-600 rounded-xl font-bold transition-colors">Confirm Registration</button>
                </form>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
"""

def get_fallback_app(domain: str, title: str, description: str = "") -> dict:
    """Return guaranteed real React app + backend for given domain."""
    from fallback_business import build_business_fallback

    if domain == "ecommerce":
        return {"app": _ECOMMERCE, "backend": _BACKEND_ECOMMERCE}
    if domain == "food_delivery":
        return {"app": _FOOD, "backend": _BACKEND_FOOD}
    if domain == "fitness":
        return {"app": _FITNESS, "backend": _BACKEND_FITNESS}
    if domain in ("business", "generic", "portfolio", "blog", "travel", "saas"):
        return build_business_fallback(title, description)
    return build_business_fallback(title, description)
