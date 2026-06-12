const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('client/build'));

// Database setup
const db = new sqlite3.Database('./food_order.db');

// Initialize database tables
db.serialize(() => {
    // Users table
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);

    // Menu items table
    db.run(`CREATE TABLE IF NOT EXISTS menu_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        available BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);

    // Orders table
    db.run(`CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        delivery_address TEXT,
        payment_method TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )`);

    // Order items table
    db.run(`CREATE TABLE IF NOT EXISTS order_items (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (item_id) REFERENCES menu_items (id)
    )`);

    // Insert sample menu items if empty
    db.get("SELECT COUNT(*) as count FROM menu_items", (err, row) => {
        if (row.count === 0) {
            const sampleItems = [
                { id: '1', name: 'Butter Chicken', description: 'Tender chicken in rich butter gravy', price: 280, category: 'Main Course', image_url: '/images/butter-chicken.jpg' },
                { id: '2', name: 'Paneer Tikka', description: 'Grilled cottage cheese with spices', price: 220, category: 'Starters', image_url: '/images/paneer-tikka.jpg' },
                { id: '3', name: 'Biryani', description: 'Fragrant rice with aromatic spices', price: 320, category: 'Main Course', image_url: '/images/biryani.jpg' },
                { id: '4', name: 'Garlic Naan', description: 'Fresh bread with garlic butter', price: 60, category: 'Bread', image_url: '/images/naan.jpg' },
                { id: '5', name: 'Samosa', description: 'Crispy pastry with potato filling', price: 40, category: 'Starters', image_url: '/images/samosa.jpg' },
                { id: '6', name: 'Lassi', description: 'Refreshing yogurt drink', price: 80, category: 'Beverages', image_url: '/images/lassi.jpg' }
            ];

            const stmt = db.prepare("INSERT INTO menu_items (id, name, description, price, category, image_url) VALUES (?, ?, ?, ?, ?, ?)");
            sampleItems.forEach(item => {
                stmt.run(item.id, item.name, item.description, item.price, item.category, item.image_url);
            });
            stmt.finalize();
        }
    });
});

// Middleware to verify JWT token
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ error: 'Access token required' });
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Invalid token' });
        }
        req.user = user;
        next();
    });
};

// Routes

// Auth routes
app.post('/api/register', async (req, res) => {
    const { email, password, name, phone, address } = req.body;
    
    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        const userId = uuidv4();
        
        db.run(
            "INSERT INTO users (id, email, password, name, phone, address) VALUES (?, ?, ?, ?, ?, ?)",
            [userId, email, hashedPassword, name, phone, address],
            function(err) {
                if (err) {
                    if (err.message.includes('UNIQUE constraint failed')) {
                        return res.status(400).json({ error: 'Email already exists' });
                    }
                    return res.status(500).json({ error: 'Registration failed' });
                }
                
                const token = jwt.sign({ userId, email, name }, JWT_SECRET);
                res.json({ token, user: { id: userId, email, name, phone, address } });
            }
        );
    } catch (error) {
        res.status(500).json({ error: 'Server error' });
    }
});

app.post('/api/login', (req, res) => {
    const { email, password } = req.body;
    
    db.get("SELECT * FROM users WHERE email = ?", [email], async (err, user) => {
        if (err || !user) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        
        const match = await bcrypt.compare(password, user.password);
        if (!match) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        
        const token = jwt.sign({ userId: user.id, email: user.email, name: user.name }, JWT_SECRET);
        res.json({ token, user: { id: user.id, email: user.email, name: user.name, phone: user.phone, address: user.address } });
    });
});

// Menu routes
app.get('/api/menu', (req, res) => {
    const category = req.query.category;
    let query = "SELECT * FROM menu_items WHERE available = 1";
    let params = [];
    
    if (category) {
        query += " AND category = ?";
        params.push(category);
    }
    
    db.all(query, params, (err, items) => {
        if (err) {
            return res.status(500).json({ error: 'Failed to fetch menu' });
        }
        res.json(items);
    });
});

app.get('/api/menu/categories', (req, res) => {
    db.all("SELECT DISTINCT category FROM menu_items WHERE available = 1", (err, categories) => {
        if (err) {
            return res.status(500).json({ error: 'Failed to fetch categories' });
        }
        res.json(categories.map(c => c.category));
    });
});

// Order routes
app.post('/api/orders', authenticateToken, (req, res) => {
    const { items, delivery_address, payment_method } = req.body;
    const userId = req.user.userId;
    
    if (!items || items.length === 0) {
        return res.status(400).json({ error: 'No items in order' });
    }
    
    const orderId = uuidv4();
    const totalAmount = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    // Start transaction
    db.serialize(() => {
        db.run("BEGIN TRANSACTION");
        
        // Insert order
        db.run(
            "INSERT INTO orders (id, user_id, total_amount, delivery_address, payment_method) VALUES (?, ?, ?, ?, ?)",
            [orderId, userId, totalAmount, delivery_address, payment_method],
            function(err) {
                if (err) {
                    db.run("ROLLBACK");
                    return res.status(500).json({ error: 'Failed to create order' });
                }
                
                // Insert order items
                const stmt = db.prepare("INSERT INTO order_items (id, order_id, item_id, quantity, price) VALUES (?, ?, ?, ?, ?)");
                let itemsInserted = 0;
                
                items.forEach(item => {
                    const orderItemId = uuidv4();
                    stmt.run(orderItemId, orderId, item.id, item.quantity, item.price, (err) => {
                        if (err) {
                            stmt.finalize();
                            db.run("ROLLBACK");
                            return res.status(500).json({ error: 'Failed to add order items' });
                        }
                        
                        itemsInserted++;
                        if (itemsInserted === items.length) {
                            stmt.finalize();
                            db.run("COMMIT");
                            res.json({ 
                                order_id: orderId, 
                                total_amount: totalAmount, 
                                status: 'pending',
                                message: 'Order placed successfully!' 
                            });
                        }
                    });
                });
            }
        );
    });
});

app.get('/api/orders', authenticateToken, (req, res) => {
    const userId = req.user.userId;
    
    db.all(
        `SELECT o.*, oi.item_id, oi.quantity, oi.price, mi.name, mi.description 
         FROM orders o 
         LEFT JOIN order_items oi ON o.id = oi.order_id 
         LEFT JOIN menu_items mi ON oi.item_id = mi.id 
         WHERE o.user_id = ? 
         ORDER BY o.created_at DESC`,
        [userId],
        (err, rows) => {
            if (err) {
                return res.status(500).json({ error: 'Failed to fetch orders' });
            }
            
            // Group order items by order
            const orders = {};
            rows.forEach(row => {
                if (!orders[row.id]) {
                    orders[row.id] = {
                        id: row.id,
                        total_amount: row.total_amount,
                        status: row.status,
                        delivery_address: row.delivery_address,
                        payment_method: row.payment_method,
                        created_at: row.created_at,
                        items: []
                    };
                }
                
                if (row.item_id) {
                    orders[row.id].items.push({
                        id: row.item_id,
                        name: row.name,
                        description: row.description,
                        quantity: row.quantity,
                        price: row.price
                    });
                }
            });
            
            res.json(Object.values(orders));
        }
    );
});

app.get('/api/orders/:id', authenticateToken, (req, res) => {
    const orderId = req.params.id;
    const userId = req.user.userId;
    
    db.get(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        [orderId, userId],
        (err, order) => {
            if (err || !order) {
                return res.status(404).json({ error: 'Order not found' });
            }
            
            db.all(
                `SELECT oi.*, mi.name, mi.description 
                 FROM order_items oi 
                 LEFT JOIN menu_items mi ON oi.item_id = mi.id 
                 WHERE oi.order_id = ?`,
                [orderId],
                (err, items) => {
                    if (err) {
                        return res.status(500).json({ error: 'Failed to fetch order items' });
                    }
                    
                    order.items = items;
                    res.json(order);
                }
            );
        }
    );
});

// Serve React app
app.get('*', (req, res) => {
    res.sendFile(__dirname + '/client/build/index.html');
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
