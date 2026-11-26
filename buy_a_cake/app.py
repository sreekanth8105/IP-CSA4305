from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import sqlite3, os, secrets
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'cake_store.db')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deployment')

CAKES = [
 ('Velvet Rose Cake','Classic','Red Velvet','Birthday',699,'Rich red velvet layers with smooth cream-cheese frosting.','https://images.unsplash.com/photo-1586788680434-30d324b2d46f?auto=format&fit=crop&w=900&q=85',1),
 ('Berry Celebration','Fruit','Strawberry','Birthday',849,'Vanilla sponge, fresh strawberries and delicate whipped cream.','https://images.unsplash.com/photo-1565958011703-44f9829ba187?auto=format&fit=crop&w=900&q=85',1),
 ('Chocolate Dream','Chocolate','Dark Chocolate','Anniversary',799,'Moist chocolate sponge finished with silky ganache.','https://images.unsplash.com/photo-1578985545062-69928b1f2a9b?auto=format&fit=crop&w=900&q=85',1),
 ('Golden Vanilla','Classic','Vanilla','Everyday',499,'A timeless vanilla cake with soft buttercream and sprinkles.','https://images.unsplash.com/photo-1571115177098-24ec42ed204d?auto=format&fit=crop&w=900&q=85',1),
 ('Lemon Sunshine','Fruit','Lemon','Celebration',649,'Bright lemon sponge with a light citrus frosting.','https://images.unsplash.com/photo-1519915028121-7d3463d20b13?auto=format&fit=crop&w=900&q=85',1),
 ('Midnight Truffle','Chocolate','Chocolate Truffle','Anniversary',999,'A premium layered truffle cake for chocolate lovers.','https://images.unsplash.com/photo-1606890737304-57a1ca8a5b62?auto=format&fit=crop&w=900&q=85',1),
 ('Pastel Dream','Designer','Butterscotch','Baby Shower',1099,'Pastel buttercream, crunchy praline and a beautiful finish.','https://images.unsplash.com/photo-1558301211-0d8c8d8f4e3f?auto=format&fit=crop&w=900&q=85',1),
 ('Coffee Caramel','Classic','Coffee','Celebration',749,'Coffee-infused sponge with caramel drizzle and cream.','https://images.unsplash.com/photo-1542826438-bd32f43d626f?auto=format&fit=crop&w=900&q=85',1),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer');
        CREATE TABLE IF NOT EXISTS cakes(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, flavor TEXT NOT NULL, occasion TEXT NOT NULL, price REAL NOT NULL, description TEXT NOT NULL, image TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, customer_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL, postal_code TEXT NOT NULL, delivery_date TEXT NOT NULL, message TEXT, payment_method TEXT NOT NULL, payment_status TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Placed', total REAL NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, cake_id INTEGER NOT NULL, cake_name TEXT NOT NULL, size TEXT NOT NULL, quantity INTEGER NOT NULL, unit_price REAL NOT NULL, message TEXT, FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(cake_id) REFERENCES cakes(id));
        ''')
        if not c.execute('SELECT id FROM users WHERE email=?', ('admin@buyacake.com',)).fetchone():
            c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)', ('Cake Admin','admin@buyacake.com',generate_password_hash('Admin123!'),'admin'))
        if c.execute('SELECT COUNT(*) n FROM cakes').fetchone()['n'] == 0:
            c.executemany('INSERT INTO cakes(name,category,flavor,occasion,price,description,image,stock) VALUES(?,?,?,?,?,?,?,?)', CAKES)

init_db()

def current_user():
    if 'user_id' not in session: return None
    with db() as c: return c.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'info'); return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u=current_user()
        if not u or u['role']!='admin': abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {'user': current_user(), 'cart_count': sum(int(x.get('quantity',1)) for x in session.get('cart',[])), 'currency': '₹', 'today': datetime.now().strftime('%Y-%m-%d')}

@app.route('/')
def home():
    q=request.args.get('q','').strip(); category=request.args.get('category',''); flavor=request.args.get('flavor',''); occasion=request.args.get('occasion',''); max_price=request.args.get('max_price','')
    sql='SELECT * FROM cakes WHERE active=1'; args=[]
    if q: sql += ' AND (name LIKE ? OR description LIKE ? OR flavor LIKE ?)'; args += [f'%{q}%']*3
    if category: sql+=' AND category=?'; args.append(category)
    if flavor: sql+=' AND flavor=?'; args.append(flavor)
    if occasion: sql+=' AND occasion=?'; args.append(occasion)
    if max_price.isdigit(): sql+=' AND price<=?'; args.append(int(max_price))
    sql+=' ORDER BY id DESC'
    with db() as c:
        cakes=c.execute(sql,args).fetchall()
        categories=[r['category'] for r in c.execute('SELECT DISTINCT category FROM cakes WHERE active=1 ORDER BY category')]
        flavors=[r['flavor'] for r in c.execute('SELECT DISTINCT flavor FROM cakes WHERE active=1 ORDER BY flavor')]
        occasions=[r['occasion'] for r in c.execute('SELECT DISTINCT occasion FROM cakes WHERE active=1 ORDER BY occasion')]
    return render_template('home.html',cakes=cakes,categories=categories,flavors=flavors,occasions=occasions,filters={'q':q,'category':category,'flavor':flavor,'occasion':occasion,'max_price':max_price})

@app.route('/cake/<int:cake_id>')
def cake_detail(cake_id):
    with db() as c: cake=c.execute('SELECT * FROM cakes WHERE id=? AND active=1',(cake_id,)).fetchone()
    if not cake: abort(404)
    return render_template('cake_detail.html',cake=cake)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        if not name or not email or len(password)<8: flash('Enter your name and email, and use a password with at least 8 characters.','error')
        else:
            try:
                with db() as c: c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name,email,generate_password_hash(password)))
                flash('Account created! You can now log in.','success'); return redirect(url_for('login'))
            except sqlite3.IntegrityError: flash('An account with that email already exists.','error')
    return render_template('auth.html',mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        with db() as c: u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if u and check_password_hash(u['password'],password):
            session.clear(); session['user_id']=u['id']; session['cart']=[]
            flash('Welcome back!','success')
            if u['role']=='admin': return redirect(url_for('admin_dashboard'))
            return redirect(request.args.get('next') or url_for('home'))
        flash('Email or password is incorrect.','error')
    return render_template('auth.html',mode='login')

@app.route('/logout')
def logout(): session.clear(); flash('You have been logged out.','info'); return redirect(url_for('home'))

@app.route('/cart')
def cart():
    items=[]; total=0
    with db() as c:
        for item in session.get('cart',[]):
            cake=c.execute('SELECT * FROM cakes WHERE id=? AND active=1',(item['cake_id'],)).fetchone()
            if cake:
                price=float(cake['price'])*({'1/2 kg':1,'1 kg':1.75,'2 kg':3.2}.get(item.get('size','1 kg'),1.75))
                subtotal=price*int(item['quantity']); total+=subtotal
                items.append({'cake':cake,'size':item.get('size','1 kg'),'quantity':int(item['quantity']),'message':item.get('message',''),'price':price,'subtotal':subtotal})
    return render_template('cart.html',items=items,total=total)

@app.route('/cart/add/<int:cake_id>', methods=['POST'])
def add_to_cart(cake_id):
    with db() as c: cake=c.execute('SELECT * FROM cakes WHERE id=? AND active=1',(cake_id,)).fetchone()
    if not cake: abort(404)
    size=request.form.get('size','1 kg'); quantity=max(1,min(10,int(request.form.get('quantity',1) or 1))); message=request.form.get('message','').strip()[:100]
    cart_items=session.get('cart',[]); cart_items.append({'cake_id':cake_id,'size':size,'quantity':quantity,'message':message}); session['cart']=cart_items
    flash(f'{cake["name"]} added to your cart.','success'); return redirect(request.referrer or url_for('cart'))

@app.route('/cart/remove/<int:index>', methods=['POST'])
def remove_from_cart(index):
    items=session.get('cart',[])
    if 0<=index<len(items): items.pop(index); session['cart']=items; flash('Item removed from cart.','info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET','POST'])
@login_required
def checkout():
    items=[]; total=0
    with db() as c:
        for item in session.get('cart',[]):
            cake=c.execute('SELECT * FROM cakes WHERE id=? AND active=1',(item['cake_id'],)).fetchone()
            if cake:
                price=float(cake['price'])*({'1/2 kg':1,'1 kg':1.75,'2 kg':3.2}.get(item.get('size','1 kg'),1.75)); subtotal=price*int(item['quantity']); total+=subtotal
                items.append({'cake':cake,'size':item.get('size','1 kg'),'quantity':int(item['quantity']),'message':item.get('message',''),'price':price,'subtotal':subtotal})
    if not items: flash('Your cart is empty. Pick a cake first!','info'); return redirect(url_for('home'))
    u=current_user()
    if request.method=='POST':
        fields={k:request.form.get(k,'').strip() for k in ['customer_name','phone','address','city','postal_code','delivery_date']}
        if not all(fields.values()): flash('Please fill in all delivery details.','error')
        elif fields['delivery_date'] < datetime.now().strftime('%Y-%m-%d'): flash('Choose today or a future delivery date.','error')
        else:
            payment=request.form.get('payment_method','Cash on delivery')
            # Demo checkout: no real payment is collected. Online payment is simulated for coursework.
            payment_status='Pending on delivery' if payment=='Cash on delivery' else 'Demo payment successful'
            with db() as c:
                cur=c.execute('INSERT INTO orders(user_id,customer_name,email,phone,address,city,postal_code,delivery_date,message,payment_method,payment_status,status,total,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (u['id'],fields['customer_name'],u['email'],fields['phone'],fields['address'],fields['city'],fields['postal_code'],fields['delivery_date'],'',payment,payment_status,'Placed',total,datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                order_id=cur.lastrowid
                for item in items:
                    c.execute('INSERT INTO order_items(order_id,cake_id,cake_name,size,quantity,unit_price,message) VALUES(?,?,?,?,?,?,?)',(order_id,item['cake']['id'],item['cake']['name'],item['size'],item['quantity'],item['price'],item['message']))
            session['cart']=[]; return redirect(url_for('order_confirmation',order_id=order_id))
    return render_template('checkout.html',items=items,total=total,u=u)

@app.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    with db() as c:
        order=c.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,current_user()['id'])).fetchone()
        if not order: abort(404)
        items=c.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall()
    return render_template('order_confirmation.html',order=order,items=items)

@app.route('/my-orders')
@login_required
def my_orders():
    with db() as c: orders=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(current_user()['id'],)).fetchall()
    return render_template('my_orders.html',orders=orders)

@app.route('/admin')
@admin_required
def admin_dashboard():
    with db() as c:
        stats={'cakes':c.execute('SELECT COUNT(*) n FROM cakes WHERE active=1').fetchone()['n'],'orders':c.execute('SELECT COUNT(*) n FROM orders').fetchone()['n'],'customers':c.execute("SELECT COUNT(*) n FROM users WHERE role='customer'").fetchone()['n'],'revenue':c.execute("SELECT COALESCE(SUM(total),0) n FROM orders WHERE status!='Cancelled'").fetchone()['n']}
        orders=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 8').fetchall()
    return render_template('admin.html',stats=stats,orders=orders)

@app.route('/admin/cakes', methods=['GET','POST'])
@admin_required
def admin_cakes():
    if request.method=='POST':
        name=request.form.get('name','').strip(); category=request.form.get('category','').strip(); flavor=request.form.get('flavor','').strip(); occasion=request.form.get('occasion','').strip(); description=request.form.get('description','').strip(); image=request.form.get('image','').strip(); price=request.form.get('price','0'); stock=request.form.get('stock','1')
        if not all([name,category,flavor,occasion,description,image]): flash('Complete every cake field.','error')
        else:
            try:
                with db() as c: c.execute('INSERT INTO cakes(name,category,flavor,occasion,price,description,image,stock) VALUES(?,?,?,?,?,?,?,?)',(name,category,flavor,occasion,max(0,float(price)),description,image,max(0,int(stock))))
                flash('Cake added to the catalogue.','success'); return redirect(url_for('admin_cakes'))
            except ValueError: flash('Price and stock must be valid numbers.','error')
    with db() as c: cakes=c.execute('SELECT * FROM cakes ORDER BY id DESC').fetchall()
    return render_template('admin_cakes.html',cakes=cakes)

@app.route('/admin/cakes/<int:cake_id>/toggle',methods=['POST'])
@admin_required
def toggle_cake(cake_id):
    with db() as c: c.execute('UPDATE cakes SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?',(cake_id,))
    flash('Cake visibility updated.','success'); return redirect(url_for('admin_cakes'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    with db() as c: orders=c.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    return render_template('admin_orders.html',orders=orders)

@app.route('/admin/orders/<int:order_id>/status',methods=['POST'])
@admin_required
def update_order_status(order_id):
    status=request.form.get('status','Placed')
    if status not in ['Placed','Confirmed','Preparing','Out for delivery','Delivered','Cancelled']: abort(400)
    with db() as c: c.execute('UPDATE orders SET status=? WHERE id=?',(status,order_id))
    flash(f'Order #{order_id} status updated.','success'); return redirect(request.referrer or url_for('admin_orders'))

@app.errorhandler(403)
def forbidden(e): return render_template('error.html',code=403,message='This page is for administrators only.'),403
@app.errorhandler(404)
def not_found(e): return render_template('error.html',code=404,message='We could not find that page.'),404

if __name__=='__main__':
    app.run(debug=True, port=int(os.environ.get('PORT',5000)))
