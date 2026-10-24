import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.jinja_env.globals["eligible_to_change"] = lambda checkin: (
    date.fromisoformat(checkin) - date.today()
).days >= 3
app.secret_key = os.environ.get("HOTEL_SECRET_KEY", "change-this-secret-key-for-real-deployment")
DB_PATH = os.path.join(os.path.dirname(__file__), "hotel.db")

ROOM_SEED = [
    ("Standard", "A comfortable room for solo travellers and couples.", 1800, 10, "Wi-Fi, air conditioning, TV"),
    ("Deluxe", "A spacious room with upgraded amenities and city views.", 2800, 8, "Wi-Fi, AC, TV, Mini fridge"),
    ("Suite", "A premium suite with a separate sitting area.", 5200, 4, "Wi-Fi, AC, TV, Lounge, Mini fridge"),
    ("Family", "A roomy option for families and small groups.", 3800, 6, "Wi-Fi, AC, TV, Extra beds"),
]
INFO_SEED = {
    "about": ("About Us", "Welcome to Grand Horizon Hotel. We offer comfortable stays, thoughtful service and convenient booking for every traveller."),
    "contact": ("Contact Us", "Email: hello@grandhorizon.example | Phone: +91 90000 00000 | Address: Chennai, Tamil Nadu"),
    "faq": ("Customer Service Q&A", "Q: What time is check-in? A: 12:00 PM.\\n\\nQ: Is Wi-Fi available? A: Yes, complimentary Wi-Fi is available.\\n\\nQ: Can I cancel? A: Eligible bookings can be cancelled up to three days before arrival."),
    "travel": ("Local Travel Guide", "Explore Chennai's beaches, museums, temples and food districts. Ask the front desk for local transport options and sightseeing suggestions."),
    "privacy": ("Privacy Policy", "We use account and booking information only to operate this demo service. Do not enter real payment details or sensitive personal information."),
    "rooms_info": ("Room Information", "Choose from Standard, Deluxe, Suite and Family rooms. Amenities and prices are shown on the Rooms page."),
}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer'
        );
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            amenities TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            room_id INTEGER NOT NULL REFERENCES rooms(id),
            checkin TEXT NOT NULL,
            checkout TEXT NOT NULL,
            guests INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Confirmed',
            payment_status TEXT NOT NULL DEFAULT 'Demo payment',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS site_info (
            slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );
        """)
        for name, description, price, quantity, amenities in ROOM_SEED:
            con.execute("""INSERT OR IGNORE INTO rooms(name,description,price,quantity,amenities)
                           VALUES(?,?,?,?,?)""", (name, description, price, quantity, amenities))
        for slug, (title, content) in INFO_SEED.items():
            con.execute("INSERT OR IGNORE INTO site_info(slug,title,content) VALUES(?,?,?)",
                        (slug, title, content))
        admin_email = os.environ.get("HOTEL_ADMIN_EMAIL", "admin@hotel.com").lower()
        admin_password = os.environ.get("HOTEL_ADMIN_PASSWORD", "Admin123!")
        existing = con.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
        if not existing:
            con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                        ("Administrator", admin_email, generate_password_hash(admin_password), "admin"))

def current_user():
    if "user_id" not in session:
        return None
    with db() as con:
        return con.execute("SELECT id,name,email,role FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def valid_dates(checkin, checkout):
    try:
        start = date.fromisoformat(checkin)
        end = date.fromisoformat(checkout)
    except (TypeError, ValueError):
        return None, None, "Please choose valid check-in and check-out dates."
    if start < date.today():
        return None, None, "Check-in cannot be in the past."
    if end <= start:
        return None, None, "Check-out must be after check-in."
    return start, end, None

def available_count(room_id, checkin, checkout, exclude_booking=None):
    with db() as con:
        room = con.execute("SELECT quantity FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            return 0
        sql = """SELECT COUNT(*) AS n FROM bookings
                 WHERE room_id=? AND status='Confirmed'
                 AND checkin < ? AND checkout > ?"""
        params = [room_id, checkout, checkin]
        if exclude_booking is not None:
            sql += " AND id != ?"
            params.append(exclude_booking)
        used = con.execute(sql, params).fetchone()["n"]
        return max(0, room["quantity"] - used)

def eligible_to_change(checkin):
    return date.fromisoformat(checkin) - date.today() >= timedelta(days=3)

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "today": date.today().isoformat()}

@app.route("/")
def index():
    with db() as con:
        rooms = con.execute("SELECT * FROM rooms ORDER BY price LIMIT 4").fetchall()
    return render_template("index.html", rooms=rooms)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "danger")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                (name, email, generate_password_hash(password)))
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email address is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Welcome back!", "success")
            target = request.args.get("next")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(target if target and target.startswith("/") else url_for("index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name cannot be empty.", "danger")
        else:
            with db() as con:
                con.execute("UPDATE users SET name=? WHERE id=?", (name, user["id"]))
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", user=current_user())

@app.route("/rooms")
def rooms():
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    guests = request.args.get("guests", "1")
    room_list = []
    with db() as con:
        all_rooms = con.execute("SELECT * FROM rooms ORDER BY price").fetchall()
    start, end, error = (None, None, None)
    if checkin or checkout:
        start, end, error = valid_dates(checkin, checkout)
        if error:
            flash(error, "warning")
    for room in all_rooms:
        count = available_count(room["id"], checkin, checkout) if start and end else room["quantity"]
        room_list.append({"room": room, "available": count})
    return render_template("rooms.html", rooms=room_list, checkin=checkin, checkout=checkout, guests=guests)

@app.route("/book/<int:room_id>", methods=["GET", "POST"])
@login_required
def book(room_id):
    with db() as con:
        room = con.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        abort(404)
    if request.method == "POST":
        checkin = request.form.get("checkin", "")
        checkout = request.form.get("checkout", "")
        try:
            guests = int(request.form.get("guests", "1"))
        except ValueError:
            guests = 0
        start, end, error = valid_dates(checkin, checkout)
        if error:
            flash(error, "danger")
        elif guests < 1 or guests > 12:
            flash("Guests must be between 1 and 12.", "danger")
        elif available_count(room_id, checkin, checkout) < 1:
            flash("Sorry, this room type is fully booked for those dates.", "danger")
        else:
            nights = (end - start).days
            total = nights * room["price"]
            # Demo checkout: no real payment details are collected.
            with db() as con:
                con.execute("""INSERT INTO bookings(user_id,room_id,checkin,checkout,guests,total,status,payment_status)
                               VALUES(?,?,?,?,?,?,?,?)""",
                            (current_user()["id"], room_id, checkin, checkout, guests, total, "Confirmed", "Demo payment completed"))
            flash(f"Booking confirmed! Demo total: ₹{total:,.2f}. No real payment was taken.", "success")
            return redirect(url_for("my_bookings"))
    return render_template("booking.html", room=room, checkin=request.args.get("checkin", ""),
                           checkout=request.args.get("checkout", ""), guests=request.args.get("guests", "1"))

@app.route("/my-bookings")
@login_required
def my_bookings():
    with db() as con:
        bookings = con.execute("""SELECT b.*, r.name AS room_name, r.price AS room_price
                                  FROM bookings b JOIN rooms r ON r.id=b.room_id
                                  WHERE b.user_id=? ORDER BY b.created_at DESC""",
                               (current_user()["id"],)).fetchall()
    return render_template("my_bookings.html", bookings=bookings, today=date.today())

def eligible_to_change(checkin):
    return date.fromisoformat(checkin) - date.today() >= timedelta(days=3)

@app.route("/booking/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def edit_booking(booking_id):
    user = current_user()
    with db() as con:
        booking = con.execute("""SELECT b.*,r.name AS room_name,r.price FROM bookings b
                                 JOIN rooms r ON r.id=b.room_id WHERE b.id=?""", (booking_id,)).fetchone()
    if not booking or (booking["user_id"] != user["id"] and user["role"] != "admin"):
        abort(404)
    if booking["status"] != "Confirmed" or not eligible_to_change(booking["checkin"]):
        flash("Changes are allowed only while the booking is confirmed and at least 3 days before arrival.", "warning")
        return redirect(url_for("admin_bookings") if user["role"] == "admin" else url_for("my_bookings"))
    if request.method == "POST":
        checkin, checkout = request.form.get("checkin", ""), request.form.get("checkout", "")
        try:
            guests = int(request.form.get("guests", "1"))
        except ValueError:
            guests = 0
        start, end, error = valid_dates(checkin, checkout)
        if error:
            flash(error, "danger")
        elif guests < 1 or guests > 12:
            flash("Guests must be between 1 and 12.", "danger")
        elif available_count(booking["room_id"], checkin, checkout, booking_id) < 1:
            flash("No rooms available for the new dates.", "danger")
        else:
            total = (end - start).days * booking["price"]
            with db() as con:
                con.execute("UPDATE bookings SET checkin=?,checkout=?,guests=?,total=? WHERE id=?",
                            (checkin, checkout, guests, total, booking_id))
            flash("Booking updated.", "success")
            return redirect(url_for("admin_bookings") if user["role"] == "admin" else url_for("my_bookings"))
    return render_template("edit_booking.html", booking=booking)

@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    user = current_user()
    with db() as con:
        booking = con.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    if not booking or (booking["user_id"] != user["id"] and user["role"] != "admin"):
        abort(404)
    allowed = user["role"] == "admin" or eligible_to_change(booking["checkin"])
    if booking["status"] != "Confirmed":
        flash("This booking is already cancelled or completed.", "warning")
    elif not allowed:
        flash("Customer cancellations are allowed only at least 3 days before arrival.", "danger")
    else:
        with db() as con:
            con.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (booking_id,))
        flash("Booking cancelled.", "success")
    return redirect(url_for("admin_bookings") if user["role"] == "admin" else url_for("my_bookings"))

@app.route("/info/<slug>", methods=["GET"])
def information(slug):
    with db() as con:
        info = con.execute("SELECT * FROM site_info WHERE slug=?", (slug,)).fetchone()
    if not info:
        abort(404)
    return render_template("information.html", info=info)

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        stats = {
            "rooms": con.execute("SELECT COUNT(*) n FROM rooms").fetchone()["n"],
            "users": con.execute("SELECT COUNT(*) n FROM users WHERE role='customer'").fetchone()["n"],
            "bookings": con.execute("SELECT COUNT(*) n FROM bookings").fetchone()["n"],
            "active": con.execute("SELECT COUNT(*) n FROM bookings WHERE status='Confirmed'").fetchone()["n"],
        }
        recent = con.execute("""SELECT b.*,u.name AS customer,r.name AS room_name FROM bookings b
                                JOIN users u ON u.id=b.user_id JOIN rooms r ON r.id=b.room_id
                                ORDER BY b.created_at DESC LIMIT 8""").fetchall()
    return render_template("admin/dashboard.html", stats=stats, bookings=recent)

@app.route("/admin/rooms", methods=["GET", "POST"])
@admin_required
def admin_rooms():
    if request.method == "POST":
        try:
            room_id = int(request.form["room_id"])
            price = float(request.form["price"])
            quantity = int(request.form["quantity"])
            if price < 0 or quantity < 0:
                raise ValueError
            with db() as con:
                con.execute("UPDATE rooms SET price=?,quantity=? WHERE id=?", (price, quantity, room_id))
            flash("Room price and quantity updated.", "success")
        except (ValueError, KeyError):
            flash("Enter a valid price and non-negative quantity.", "danger")
        return redirect(url_for("admin_rooms"))
    with db() as con:
        rooms = con.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    return render_template("admin/rooms.html", rooms=rooms)

@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    with db() as con:
        bookings = con.execute("""SELECT b.*,u.name AS customer,u.email,r.name AS room_name
                                  FROM bookings b JOIN users u ON u.id=b.user_id
                                  JOIN rooms r ON r.id=b.room_id ORDER BY b.created_at DESC""").fetchall()
    return render_template("admin/bookings.html", bookings=bookings)

@app.route("/admin/info", methods=["GET", "POST"])
@admin_required
def admin_info():
    if request.method == "POST":
        slug = request.form.get("slug", "")
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if slug not in INFO_SEED or not title or not content:
            flash("Please provide a title and content for a valid page.", "danger")
        else:
            with db() as con:
                con.execute("UPDATE site_info SET title=?,content=? WHERE slug=?", (title, content, slug))
            flash("Website information updated.", "success")
        return redirect(url_for("admin_info"))
    with db() as con:
        pages = con.execute("SELECT * FROM site_info ORDER BY title").fetchall()
    return render_template("admin/info.html", pages=pages)

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
