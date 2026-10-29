import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("BUS_SECRET_KEY", "change-this-secret-key-before-deployment")
DB_PATH = os.path.join(os.path.dirname(__file__), "bus.db")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS buses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure TEXT NOT NULL,
            arrival TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            total_seats INTEGER NOT NULL CHECK(total_seats > 0),
            photo_url TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            bus_id INTEGER NOT NULL REFERENCES buses(id),
            passenger_name TEXT NOT NULL,
            passenger_age INTEGER NOT NULL,
            passenger_phone TEXT NOT NULL,
            seats TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Confirmed',
            payment_status TEXT NOT NULL DEFAULT 'Demo payment completed',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            bus_id INTEGER NOT NULL REFERENCES buses(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS news(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        for name, desc in [
            ("Volvo", "Premium air-conditioned coach"),
            ("Sleeper", "Comfortable sleeper coach"),
            ("Coach", "Standard intercity coach"),
            ("AC Seater", "Air-conditioned reclining seats"),
        ]:
            con.execute("INSERT OR IGNORE INTO categories(name,description) VALUES(?,?)", (name, desc))
        admin_email = os.environ.get("BUS_ADMIN_EMAIL", "admin@bus.com").lower()
        admin_password = os.environ.get("BUS_ADMIN_PASSWORD", "Admin123!")
        if not con.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone():
            con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                        ("Administrator", admin_email, generate_password_hash(admin_password), "admin"))
        if con.execute("SELECT COUNT(*) AS n FROM buses").fetchone()["n"] == 0:
            categories = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM categories")}
            today = date.today()
            demo_buses = [
                ("Southern Star Express", categories["Volvo"], "Chennai", "Bengaluru", "21:00", "05:30", today.isoformat(), 950, 36, "", "Premium Volvo service with charging points and air conditioning."),
                ("Night Owl Sleeper", categories["Sleeper"], "Chennai", "Coimbatore", "20:30", "06:00", today.isoformat(), 1100, 30, "", "Sleeper coach for a comfortable overnight journey."),
                ("CityLink Coach", categories["Coach"], "Bengaluru", "Mysuru", "09:00", "12:30", today.isoformat(), 350, 40, "", "Affordable daytime intercity coach."),
                ("Coastal Comfort", categories["AC Seater"], "Chennai", "Pondicherry", "07:30", "10:45", today.isoformat(), 450, 32, "", "AC seater service for a short coastal trip."),
            ]
            con.executemany("""INSERT INTO buses(name,category_id,source,destination,departure,arrival,travel_date,price,total_seats,photo_url,description)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?)""", demo_buses)
        if con.execute("SELECT COUNT(*) AS n FROM news").fetchone()["n"] == 0:
            con.execute("INSERT INTO news(title,body) VALUES(?,?)",
                        ("Welcome aboard", "Welcome to BusWay. Search your route and reserve a seat for your next trip."))

def user_now():
    if not session.get("user_id"):
        return None
    with db() as con:
        return con.execute("SELECT id,name,email,role FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not user_now():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = user_now()
        if not user or user["role"] != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def occupied_seats(bus_id, exclude_booking=None):
    sql = "SELECT seats FROM bookings WHERE bus_id=? AND status='Confirmed'"
    params = [bus_id]
    if exclude_booking:
        sql += " AND id != ?"
        params.append(exclude_booking)
    with db() as con:
        rows = con.execute(sql, params).fetchall()
    occupied = set()
    for row in rows:
        occupied.update(s.strip() for s in row["seats"].split(",") if s.strip())
    return occupied

def bus_with_category(bus_id):
    with db() as con:
        return con.execute("""SELECT b.*,c.name AS category_name,c.description AS category_description
                              FROM buses b JOIN categories c ON c.id=b.category_id WHERE b.id=?""",
                           (bus_id,)).fetchone()

@app.context_processor
def inject_globals():
    return {"current_user": user_now(), "today": date.today().isoformat()}

@app.route("/")
def index():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get("travel_date", "").strip()
    sql = """SELECT b.*,c.name AS category_name FROM buses b
             JOIN categories c ON c.id=b.category_id WHERE b.active=1"""
    params = []
    if source:
        sql += " AND lower(b.source) LIKE lower(?)"; params.append(f"%{source}%")
    if destination:
        sql += " AND lower(b.destination) LIKE lower(?)"; params.append(f"%{destination}%")
    if travel_date:
        sql += " AND b.travel_date=?"; params.append(travel_date)
    sql += " ORDER BY b.travel_date,b.departure"
    with db() as con:
        buses = con.execute(sql, params).fetchall()
        news_items = con.execute("SELECT * FROM news ORDER BY created_at DESC LIMIT 3").fetchall()
    bus_cards = []
    for bus in buses:
        bus_cards.append({"bus": bus, "available": max(0, bus["total_seats"] - len(occupied_seats(bus["id"])))})
    return render_template("index.html", buses=bus_cards, news_items=news_items,
                           source=source, destination=destination, travel_date=travel_date)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password of at least 8 characters.", "danger")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                (name, email, generate_password_hash(password)))
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This email is already registered.", "danger")
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
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            target = request.args.get("next", "")
            return redirect(target if target.startswith("/") else url_for("index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        with db() as con:
            row = con.execute("SELECT * FROM users WHERE id=?", (user_now()["id"],)).fetchone()
            if not check_password_hash(row["password_hash"], old):
                flash("Current password is incorrect.", "danger")
            elif len(new) < 8:
                flash("New password must contain at least 8 characters.", "danger")
            else:
                con.execute("UPDATE users SET password_hash=? WHERE id=?",
                            (generate_password_hash(new), row["id"]))
                flash("Password changed successfully.", "success")
                return redirect(url_for("index"))
    return render_template("change_password.html")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = user_now()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name cannot be empty.", "danger")
        else:
            with db() as con:
                con.execute("UPDATE users SET name=? WHERE id=?", (name, user["id"]))
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", user=user_now())

@app.route("/bus/<int:bus_id>")
def bus_detail(bus_id):
    bus = bus_with_category(bus_id)
    if not bus:
        abort(404)
    occupied = occupied_seats(bus_id)
    seats = [{"label": f"{n:02d}", "taken": f"{n:02d}" in occupied} for n in range(1, bus["total_seats"] + 1)]
    with db() as con:
        comments = con.execute("""SELECT c.*,u.name AS author FROM comments c JOIN users u ON u.id=c.user_id
                                  WHERE c.bus_id=? ORDER BY c.created_at DESC""", (bus_id,)).fetchall()
    return render_template("bus_detail.html", bus=bus, seats=seats, comments=comments)

@app.route("/book/<int:bus_id>", methods=["GET", "POST"])
@login_required
def book(bus_id):
    bus = bus_with_category(bus_id)
    if not bus or not bus["active"]:
        abort(404)
    if request.method == "POST":
        passenger = request.form.get("passenger_name", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            age = int(request.form.get("age", "0"))
        except ValueError:
            age = 0
        selected = sorted(set(request.form.getlist("seats")))
        valid_labels = {f"{n:02d}" for n in range(1, bus["total_seats"] + 1)}
        if not passenger or not phone or age < 1 or age > 120:
            flash("Enter valid passenger name, age and phone number.", "danger")
        elif not selected or any(s not in valid_labels for s in selected):
            flash("Please select at least one valid seat.", "danger")
        else:
            with db() as con:
                con.execute("BEGIN IMMEDIATE")
                current = con.execute("SELECT total_seats FROM buses WHERE id=? AND active=1", (bus_id,)).fetchone()
                occupied = occupied_seats(bus_id)
                if not current or any(s in occupied for s in selected):
                    flash("One or more selected seats are no longer available. Please select again.", "danger")
                else:
                    total = len(selected) * bus["price"]
                    con.execute("""INSERT INTO bookings(user_id,bus_id,passenger_name,passenger_age,passenger_phone,seats,total)
                                   VALUES(?,?,?,?,?,?,?)""",
                                (user_now()["id"], bus_id, passenger, age, phone, ",".join(selected), total))
                    booking_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                    flash(f"Ticket confirmed! Booking #{booking_id}. Demo total ₹{total:,.2f}; no real payment was taken.", "success")
                    return redirect(url_for("my_bookings"))
    occupied = occupied_seats(bus_id)
    seats = [{"label": f"{n:02d}", "taken": f"{n:02d}" in occupied} for n in range(1, bus["total_seats"] + 1)]
    return render_template("book.html", bus=bus, seats=seats)

@app.route("/my-bookings")
@login_required
def my_bookings():
    with db() as con:
        bookings = con.execute("""SELECT bk.*,b.name AS bus_name,b.source,b.destination,b.travel_date,b.departure
                                  FROM bookings bk JOIN buses b ON b.id=bk.bus_id
                                  WHERE bk.user_id=? ORDER BY bk.created_at DESC""",
                               (user_now()["id"],)).fetchall()
    return render_template("my_bookings.html", bookings=bookings)

@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    user = user_now()
    with db() as con:
        booking = con.execute("""SELECT bk.*,b.travel_date FROM bookings bk JOIN buses b ON b.id=bk.bus_id
                                 WHERE bk.id=?""", (booking_id,)).fetchone()
        if not booking or (booking["user_id"] != user["id"] and user["role"] != "admin"):
            abort(404)
        if booking["status"] != "Confirmed":
            flash("This booking is already cancelled.", "warning")
        elif user["role"] != "admin" and booking["travel_date"] < date.today().isoformat():
            flash("Past travel bookings cannot be cancelled.", "danger")
        else:
            con.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (booking_id,))
            flash("Ticket cancelled.", "success")
    return redirect(url_for("admin_bookings") if user["role"] == "admin" else url_for("my_bookings"))

@app.route("/bus/<int:bus_id>/comment", methods=["POST"])
@login_required
def add_comment(bus_id):
    body = request.form.get("body", "").strip()
    if not bus_with_category(bus_id):
        abort(404)
    if not body or len(body) > 1000:
        flash("Comment must be between 1 and 1000 characters.", "danger")
    else:
        with db() as con:
            con.execute("INSERT INTO comments(user_id,bus_id,body) VALUES(?,?,?)",
                        (user_now()["id"], bus_id, body))
        flash("Comment posted.", "success")
    return redirect(url_for("bus_detail", bus_id=bus_id))

@app.route("/news")
def news_page():
    with db() as con:
        news_items = con.execute("SELECT * FROM news ORDER BY created_at DESC").fetchall()
    return render_template("news.html", news_items=news_items)

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        stats = {
            "users": con.execute("SELECT COUNT(*) n FROM users WHERE role='customer'").fetchone()["n"],
            "buses": con.execute("SELECT COUNT(*) n FROM buses").fetchone()["n"],
            "bookings": con.execute("SELECT COUNT(*) n FROM bookings").fetchone()["n"],
            "revenue": con.execute("SELECT COALESCE(SUM(total),0) n FROM bookings WHERE status='Confirmed'").fetchone()["n"],
        }
        recent = con.execute("""SELECT bk.*,u.name AS customer,b.name AS bus_name
                                FROM bookings bk JOIN users u ON u.id=bk.user_id JOIN buses b ON b.id=bk.bus_id
                                ORDER BY bk.created_at DESC LIMIT 8""").fetchall()
    return render_template("admin/dashboard.html", stats=stats, bookings=recent)

@app.route("/admin/buses", methods=["GET", "POST"])
@admin_required
def admin_buses():
    with db() as con:
        categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        try:
            bus_id = request.form.get("bus_id", "").strip()
            name = request.form["name"].strip()
            category_id = int(request.form["category_id"])
            source = request.form["source"].strip()
            destination = request.form["destination"].strip()
            departure = request.form["departure"]
            arrival = request.form["arrival"]
            travel_date = date.fromisoformat(request.form["travel_date"]).isoformat()
            price = float(request.form["price"])
            seats = int(request.form["total_seats"])
            photo = request.form.get("photo_url", "").strip()
            description = request.form.get("description", "").strip()
            if not name or not source or not destination or source.lower() == destination.lower() or price < 0 or seats < 1:
                raise ValueError
            with db() as con:
                if bus_id:
                    con.execute("""UPDATE buses SET name=?,category_id=?,source=?,destination=?,departure=?,arrival=?,
                                   travel_date=?,price=?,total_seats=?,photo_url=?,description=? WHERE id=?""",
                                (name,category_id,source,destination,departure,arrival,travel_date,price,seats,photo,description,int(bus_id)))
                else:
                    con.execute("""INSERT INTO buses(name,category_id,source,destination,departure,arrival,travel_date,
                                   price,total_seats,photo_url,description) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                (name,category_id,source,destination,departure,arrival,travel_date,price,seats,photo,description))
            flash("Bus saved successfully.", "success")
        except (ValueError, KeyError, sqlite3.IntegrityError):
            flash("Please check all bus fields and enter valid values.", "danger")
        return redirect(url_for("admin_buses"))
    with db() as con:
        buses = con.execute("""SELECT b.*,c.name AS category_name FROM buses b JOIN categories c ON c.id=b.category_id
                               ORDER BY b.travel_date,b.departure""").fetchall()
    return render_template("admin/buses.html", buses=buses, categories=categories)

@app.route("/admin/bus/<int:bus_id>/toggle", methods=["POST"])
@admin_required
def toggle_bus(bus_id):
    with db() as con:
        row = con.execute("SELECT active FROM buses WHERE id=?", (bus_id,)).fetchone()
        if not row: abort(404)
        con.execute("UPDATE buses SET active=? WHERE id=?", (0 if row["active"] else 1, bus_id))
    flash("Bus availability updated.", "success")
    return redirect(url_for("admin_buses"))

@app.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if not name:
            flash("Category name is required.", "danger")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO categories(name,description) VALUES(?,?)", (name, desc))
                flash("Category added.", "success")
            except sqlite3.IntegrityError:
                flash("That category already exists.", "danger")
        return redirect(url_for("admin_categories"))
    with db() as con:
        categories = con.execute("""SELECT c.*,COUNT(b.id) AS bus_count FROM categories c
                                    LEFT JOIN buses b ON b.category_id=c.id GROUP BY c.id ORDER BY c.name""").fetchall()
    return render_template("admin/categories.html", categories=categories)

@app.route("/admin/users")
@admin_required
def admin_users():
    with db() as con:
        users = con.execute("""SELECT u.id,u.name,u.email,u.role,u.created_at,COUNT(b.id) AS bookings
                               FROM users u LEFT JOIN bookings b ON b.user_id=u.id
                               GROUP BY u.id ORDER BY u.created_at DESC""").fetchall()
    return render_template("admin/users.html", users=users)

@app.route("/admin/comments")
@admin_required
def admin_comments():
    with db() as con:
        comments = con.execute("""SELECT c.*,u.name AS author,b.name AS bus_name FROM comments c
                                  JOIN users u ON u.id=c.user_id JOIN buses b ON b.id=c.bus_id
                                  ORDER BY c.created_at DESC""").fetchall()
    return render_template("admin/comments.html", comments=comments)

@app.route("/admin/comment/<int:comment_id>/delete", methods=["POST"])
@admin_required
def delete_comment(comment_id):
    with db() as con:
        con.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    flash("Comment removed.", "success")
    return redirect(url_for("admin_comments"))

@app.route("/admin/news", methods=["GET", "POST"])
@admin_required
def admin_news():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if title and body:
            with db() as con:
                con.execute("INSERT INTO news(title,body) VALUES(?,?)", (title,body))
            flash("News item published.", "success")
        else:
            flash("Enter a title and news content.", "danger")
        return redirect(url_for("admin_news"))
    with db() as con:
        items = con.execute("SELECT * FROM news ORDER BY created_at DESC").fetchall()
    return render_template("admin/news.html", items=items)

@app.route("/admin/news/<int:news_id>/delete", methods=["POST"])
@admin_required
def delete_news(news_id):
    with db() as con:
        con.execute("DELETE FROM news WHERE id=?", (news_id,))
    flash("News item deleted.", "success")
    return redirect(url_for("admin_news"))

@app.route("/admin/reports")
@admin_required
def admin_reports():
    with db() as con:
        summary = con.execute("""SELECT COUNT(*) AS bookings,
                                 SUM(CASE WHEN status='Confirmed' THEN 1 ELSE 0 END) AS confirmed,
                                 SUM(CASE WHEN status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                                 COALESCE(SUM(CASE WHEN status='Confirmed' THEN total ELSE 0 END),0) AS revenue
                                 FROM bookings""").fetchone()
        by_bus = con.execute("""SELECT b.name,b.source,b.destination,COUNT(bk.id) AS bookings,
                                COALESCE(SUM(CASE WHEN bk.status='Confirmed' THEN bk.total ELSE 0 END),0) AS revenue
                                FROM buses b LEFT JOIN bookings bk ON bk.bus_id=b.id
                                GROUP BY b.id ORDER BY bookings DESC""").fetchall()
    return render_template("admin/reports.html", summary=summary, by_bus=by_bus)

@app.route("/admin/reports.csv")
@admin_required
def reports_csv():
    with db() as con:
        rows = con.execute("""SELECT bk.id,u.name,u.email,b.name AS bus,b.source,b.destination,b.travel_date,
                              bk.seats,bk.total,bk.status,bk.created_at FROM bookings bk
                              JOIN users u ON u.id=bk.user_id JOIN buses b ON b.id=bk.bus_id
                              ORDER BY bk.created_at DESC""").fetchall()
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Booking ID","Passenger","Email","Bus","Source","Destination","Travel Date","Seats","Total","Status","Created At"])
    for row in rows:
        writer.writerow(list(row))
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=bus_booking_report.csv"
    return response

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
