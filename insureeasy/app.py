import csv
import io
import json
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, abort

BASE_DIR = Path(__file__).resolve().parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "replace-this-demo-secret-before-deployment")
DB_PATH = BASE_DIR / "workspace.db"

FIELDS = CONFIG["fields"]
FIELD_MAP = {f["key"]: f for f in FIELDS}
STATUS_FIELD = next((f["key"] for f in FIELDS if f["key"] == "status"), None)
PRIMARY_KEY = FIELDS[0]["key"]
SECONDARY_KEY = FIELDS[1]["key"] if len(FIELDS) > 1 else FIELDS[0]["key"]
PRIMARY_LABEL = FIELDS[0]["label"]

def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with connect_db() as db:
        cols = ", ".join('"' + f["key"] + '" TEXT NOT NULL DEFAULT \'\'' for f in FIELDS)
        db.execute(f"CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, {cols})")
        if db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0:
            for item in CONFIG["seed"]:
                keys = list(item.keys())
                placeholders = ",".join("?" for _ in keys)
                db.execute(f"INSERT INTO records ({','.join(chr(34)+k+chr(34) for k in keys)}) VALUES ({placeholders})", [item[k] for k in keys])
        db.execute("CREATE INDEX IF NOT EXISTS idx_records_created_at ON records(created_at)")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def clean_record(row):
    record = dict(row)
    status_value = record.get(STATUS_FIELD, "") if STATUS_FIELD else ""
    normalized = str(status_value).lower()
    if any(word in normalized for word in ("complete", "paid", "available", "active", "published", "resolved", "delivered", "confirmed", "in stock", "closed")):
        status_class = "green"
    elif any(word in normalized for word in ("urgent", "critical", "failed", "cancel", "out of stock", "lapsed", "rejected")):
        status_class = "red"
    elif any(word in normalized for word in ("pending", "request", "scheduled", "progress", "offer", "low stock", "preparing", "draft")):
        status_class = "orange"
    elif any(word in normalized for word in ("open", "routine")):
        status_class = "blue"
    else:
        status_class = "purple"
    record["status_value"] = status_value
    record["status_class"] = status_class
    return record

def get_records():
    with connect_db() as db:
        rows = db.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
    return [clean_record(r) for r in rows]

def template_context(active, section):
    return dict(title=CONFIG["title"], subtitle=CONFIG["subtitle"], icon=CONFIG["icon"],
                plural=CONFIG["plural"], singular=CONFIG["singular"], metrics=CONFIG["metrics"],
                fields=FIELDS, active=active, section=section)

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        expected_user = os.environ.get("DEMO_USERNAME", "admin")
        expected_pass = os.environ.get("DEMO_PASSWORD", "admin123")
        if username == expected_user and password == expected_pass:
            session.clear()
            session["logged_in"] = True
            flash("Welcome back. You are signed in.", "success")
            destination = request.args.get("next", "")
            return redirect(destination if destination.startswith("/") and not destination.startswith("//") else url_for("index"))
        flash("That username or password did not match the demo credentials.", "error")
    return render_template("login.html", title=CONFIG["title"], icon=CONFIG["icon"])

@app.route("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    records = get_records()
    counts = {}
    for metric in CONFIG["metrics"]:
        counts[metric] = sum(1 for r in records if r.get(STATUS_FIELD) == metric) if STATUS_FIELD else 0
    ctx = template_context("dashboard", "Overview")
    ctx.update(records=records, total=len(records), counts=counts, primary_key=PRIMARY_KEY,
               secondary_key=SECONDARY_KEY, primary_label=PRIMARY_LABEL)
    return render_template("dashboard.html", **ctx)

@app.route("/records")
@login_required
def records():
    q = request.args.get("q", "").strip().lower()
    selected_status = request.args.get("status", "").strip()
    data = get_records()
    if q:
        data = [r for r in data if any(q in str(r.get(f["key"], "")).lower() for f in FIELDS)]
    if selected_status and STATUS_FIELD:
        data = [r for r in data if r.get(STATUS_FIELD) == selected_status]
    ctx = template_context("records", CONFIG["plural"])
    ctx.update(records=data, q=q, selected_status=selected_status,
               status_options=FIELD_MAP[STATUS_FIELD]["options"] if STATUS_FIELD else [])
    return render_template("records.html", **ctx)

@app.route("/records/new", methods=["GET", "POST"])
@login_required
def new_record():
    if request.method == "POST":
        values = {}
        for field in FIELDS:
            value = request.form.get(field["key"], "").strip()
            if field.get("required") and not value:
                flash(f'{field["label"]} is required.', "error")
                return render_template("form.html", **template_context("records", "Create record"), record=None)
            if field["type"] == "select" and value and value not in field.get("options", []):
                flash(f'Choose a valid option for {field["label"]}.', "error")
                return render_template("form.html", **template_context("records", "Create record"), record=None)
            if field["type"] == "number" and value:
                try:
                    if float(value) < 0: raise ValueError()
                except ValueError:
                    flash(f'{field["label"]} must be a non-negative number.', "error")
                    return render_template("form.html", **template_context("records", "Create record"), record=None)
            values[field["key"]] = value
        keys = list(values)
        with connect_db() as db:
            db.execute(f"INSERT INTO records ({','.join(chr(34)+k+chr(34) for k in keys)}) VALUES ({','.join('?' for _ in keys)})", [values[k] for k in keys])
        flash(f'{CONFIG["entity"]} created successfully.', "success")
        return redirect(url_for("records"))
    return render_template("form.html", **template_context("records", "Create record"), record=None)

@app.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(record_id):
    with connect_db() as db:
        row = db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
    if row is None: abort(404)
    record = dict(row)
    if request.method == "POST":
        values = {}
        for field in FIELDS:
            value = request.form.get(field["key"], "").strip()
            if field.get("required") and not value:
                flash(f'{field["label"]} is required.', "error")
                return render_template("form.html", **template_context("records", "Edit record"), record=record)
            if field["type"] == "select" and value and value not in field.get("options", []):
                flash(f'Choose a valid option for {field["label"]}.', "error")
                return render_template("form.html", **template_context("records", "Edit record"), record=record)
            if field["type"] == "number" and value:
                try:
                    if float(value) < 0: raise ValueError()
                except ValueError:
                    flash(f'{field["label"]} must be a non-negative number.', "error")
                    return render_template("form.html", **template_context("records", "Edit record"), record=record)
            values[field["key"]] = value
        assignments = ",".join('"' + k + '"=?' for k in values)
        with connect_db() as db:
            db.execute(f"UPDATE records SET {assignments} WHERE id=?", [values[k] for k in values] + [record_id])
        flash(f'{CONFIG["entity"]} updated successfully.', "success")
        return redirect(url_for("records"))
    return render_template("form.html", **template_context("records", "Edit record"), record=record)

@app.route("/records/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_record(record_id):
    with connect_db() as db:
        cursor = db.execute("DELETE FROM records WHERE id=?", (record_id,))
    if cursor.rowcount:
        flash(f'{CONFIG["entity"]} deleted.', "success")
    else:
        flash("That record no longer exists.", "error")
    return redirect(url_for("records"))

@app.route("/export.csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f["label"] for f in FIELDS])
    for record in get_records():
        writer.writerow([record.get(f["key"], "") for f in FIELDS])
    response = make_response("\\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{CONFIG["title"].lower().replace(" ", "_")}_records.csv"'
    return response

@app.errorhandler(404)
def not_found(_error):
    return render_template("base.html", title=CONFIG["title"], subtitle=CONFIG["subtitle"],
        icon=CONFIG["icon"], plural=CONFIG["plural"], singular=CONFIG["singular"],
        active="", section="Not found"), 404

with app.app_context():
    init_db()

if __name__ == "__main__":
    print(f"\\n{CONFIG['title']} is starting...")
    print("Demo login: admin / admin123")
    print("Open http://127.0.0.1:5000")
    app.run(debug=True)
