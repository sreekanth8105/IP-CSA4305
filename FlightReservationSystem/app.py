import os, sqlite3, secrets, string, csv, io
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.secret_key=os.environ.get("FLIGHT_SECRET_KEY","change-this-secret-key-before-deployment")
DB=os.path.join(os.path.dirname(__file__),"airline.db")
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def init_db():
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT DEFAULT 'passenger',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS flights(id INTEGER PRIMARY KEY,number TEXT UNIQUE NOT NULL,name TEXT NOT NULL,origin TEXT NOT NULL,destination TEXT NOT NULL,departure TEXT NOT NULL,arrival TEXT NOT NULL,journey_date TEXT NOT NULL,zone TEXT DEFAULT 'South',active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY,flight_id INTEGER REFERENCES flights(id),class_name TEXT NOT NULL,capacity INTEGER NOT NULL,fare REAL NOT NULL,UNIQUE(flight_id,class_name));
  CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,booking_code TEXT UNIQUE NOT NULL,user_id INTEGER REFERENCES users(id),flight_id INTEGER REFERENCES flights(id),class_name TEXT,journey_date TEXT,passenger_names TEXT,passenger_ages TEXT,passenger_count INTEGER,total_fare REAL,status TEXT DEFAULT 'CONFIRMED',payment_mode TEXT,payment_status TEXT,refund_amount REAL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS refund_rules(id INTEGER PRIMARY KEY,min_days INTEGER,max_days INTEGER,refund_percent REAL,label TEXT);
  CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),rating INTEGER NOT NULL,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  """)
  email=os.environ.get("FLIGHT_ADMIN_EMAIL","admin@aerovista.demo").lower()
  if not c.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
   c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",("Airline Administrator",email,generate_password_hash(os.environ.get("FLIGHT_ADMIN_PASSWORD","Admin123!")),"admin"))
  if not c.execute("SELECT id FROM flights LIMIT 1").fetchone():
   d=date.today().isoformat()
   ts=[("AV 201","AeroVista Chennai","Chennai","Madurai","06:00","13:15",d,"Asia"),("SK 408","Skyline Airways","Chennai","Mumbai","07:15","14:30",d,"Asia"),("BH 612","Blue Horizon Air","Bengaluru","Hyderabad","09:00","11:45",d,"Asia"),("NJ 905","NightJet Airways","Chennai","Bengaluru","21:30","05:30",d,"Asia")]
   for t in ts:
    c.execute("INSERT INTO flights(number,name,origin,destination,departure,arrival,journey_date,zone) VALUES(?,?,?,?,?,?,?,?)",t)
    tid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.executemany("INSERT INTO classes(flight_id,class_name,capacity,fare) VALUES(?,?,?,?)",[(tid,"Economy",180,4200),(tid,"Premium Economy",48,6800),(tid,"Business",24,14500),(tid,"First Class",12,28000)])
  if not c.execute("SELECT id FROM refund_rules LIMIT 1").fetchone():
   c.executemany("INSERT INTO refund_rules(min_days,max_days,refund_percent,label) VALUES(?,?,?,?)",[(7,36500,90,"7+ days before departure"),(3,6,75,"3–6 days before departure"),(1,2,50,"1–2 days before departure"),(0,0,0,"Departure day or past journey")])
def me():
 if not session.get("uid"): return None
 with db() as c: return c.execute("SELECT id,name,email,role FROM users WHERE id=?",(session["uid"],)).fetchone()
def login_required(f):
 @wraps(f)
 def w(*a,**k):
  if not me(): flash("Please log in first.","warning"); return redirect(url_for("login"))
  return f(*a,**k)
 return w
def admin_required(f):
 @wraps(f)
 def w(*a,**k):
  u=me()
  if not u or u["role"]!="admin": flash("Administrator access required.","danger"); return redirect(url_for("login"))
  return f(*a,**k)
 return w
def available(tid,cls,d):
 with db() as c:
  n=c.execute("SELECT COALESCE(SUM(passenger_count),0) n FROM bookings WHERE flight_id=? AND class_name=? AND journey_date=? AND status='CONFIRMED'",(tid,cls["class_name"],d)).fetchone()["n"]
 return max(0,cls["capacity"]-n)
def flight(tid):
 with db() as c: return c.execute("SELECT * FROM flights WHERE id=?",(tid,)).fetchone()
def refund_pct(d):
 try: days=(date.fromisoformat(d)-date.today()).days
 except: return 0
 with db() as c: r=c.execute("SELECT refund_percent FROM refund_rules WHERE min_days<=? AND max_days>=? ORDER BY min_days DESC LIMIT 1",(days,days)).fetchone()
 return r["refund_percent"] if r else 0
@app.context_processor
def ctx(): return {"current_user":me(),"today":date.today().isoformat()}
@app.route("/")
def index():
 o=request.args.get("origin","").strip(); dest=request.args.get("destination","").strip(); d=request.args.get("journey_date","").strip()
 sql="SELECT * FROM flights WHERE active=1"; p=[]
 if o: sql+=" AND lower(origin) LIKE lower(?)"; p.append("%"+o+"%")
 if dest: sql+=" AND lower(destination) LIKE lower(?)"; p.append("%"+dest+"%")
 if d: sql+=" AND journey_date=?"; p.append(d)
 sql+=" ORDER BY journey_date,departure"
 with db() as c:
  ts=c.execute(sql,p).fetchall(); cards=[]
  for t in ts:
   cs=c.execute("SELECT * FROM classes WHERE flight_id=? ORDER BY fare",(t["id"],)).fetchall()
   cards.append({"flight":t,"classes":[{"class":x,"available":available(t["id"],x,t["journey_date"])} for x in cs]})
 return render_template("index.html",cards=cards,origin=o,destination=dest,journey_date=d)
@app.route("/register",methods=["GET","POST"])
def register():
 if request.method=="POST":
  n=request.form.get("name","").strip(); e=request.form.get("email","").strip().lower(); p=request.form.get("password","")
  if not n or not e or len(p)<8: flash("Enter your name/email and a password of at least 8 characters.","danger")
  else:
   try:
    with db() as c: c.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",(n,e,generate_password_hash(p)))
    flash("Account created. Please log in.","success"); return redirect(url_for("login"))
   except sqlite3.IntegrityError: flash("Email already registered.","danger")
 return render_template("register.html")
@app.route("/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  e=request.form.get("email","").strip().lower(); p=request.form.get("password","")
  with db() as c: u=c.execute("SELECT * FROM users WHERE email=?",(e,)).fetchone()
  if u and check_password_hash(u["password_hash"],p):
   session.clear(); session["uid"]=u["id"]; flash("Welcome back!","success")
   return redirect(url_for("admin") if u["role"]=="admin" else url_for("index"))
  flash("Invalid email or password.","danger")
 return render_template("login.html")
@app.route("/forgot-password",methods=["GET","POST"])
def forgot_password():
 if request.method=="POST":
  email=request.form.get("email"," ").strip().lower(); new=request.form.get("new_password","")
  if len(new)<8: flash("Use a password with at least 8 characters.","danger")
  else:
   with db() as c: cur=c.execute("UPDATE users SET password_hash=? WHERE email=? AND role='passenger'",(generate_password_hash(new),email))
   if cur.rowcount: flash("Demo password reset complete. You can log in now.","success"); return redirect(url_for("login"))
   flash("No customer account was found for that email.","danger")
 return render_template("forgot_password.html")
@app.route("/feedback",methods=["GET","POST"])
@login_required
def feedback():
 if request.method=="POST":
  try: rating=int(request.form.get("rating","5")); message=request.form.get("message","").strip()
  except ValueError: rating=0; message=""
  if rating not in range(1,6) or not message: flash("Choose a rating and enter feedback.","danger")
  else:
   with db() as c: c.execute("INSERT INTO feedback(user_id,rating,message) VALUES(?,?,?)",(me()["id"],rating,message))
   flash("Thanks for sharing your feedback!","success"); return redirect(url_for("index"))
 return render_template("feedback.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("index"))
@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
 u=me()
 if request.method=="POST":
  n=request.form.get("name","").strip()
  if n:
   with db() as c: c.execute("UPDATE users SET name=? WHERE id=?",(n,u["id"]))
   flash("Profile updated.","success"); return redirect(url_for("profile"))
  flash("Name is required.","danger")
 return render_template("profile.html",user=me())
@app.route("/change-password",methods=["GET","POST"])
@login_required
def change_password():
 if request.method=="POST":
  old=request.form.get("old_password",""); new=request.form.get("new_password","")
  with db() as c:
   u=c.execute("SELECT * FROM users WHERE id=?",(me()["id"],)).fetchone()
   if not check_password_hash(u["password_hash"],old): flash("Current password is incorrect.","danger")
   elif len(new)<8: flash("Use at least 8 characters.","danger")
   else:
    c.execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(new),u["id"])); flash("Password changed.","success"); return redirect(url_for("index"))
 return render_template("change_password.html")
@app.route("/flight/<int:tid>")
def flight_detail(tid):
 t=flight(tid)
 if not t: abort(404)
 with db() as c: cs=c.execute("SELECT * FROM classes WHERE flight_id=? ORDER BY fare",(tid,)).fetchall()
 return render_template("flight_detail.html",t=t,classes=[{"class":x,"available":available(tid,x,t["journey_date"])} for x in cs])
@app.route("/book/<int:tid>/<int:cid>",methods=["GET","POST"])
@login_required
def book(tid,cid):
 t=flight(tid)
 with db() as c: cl=c.execute("SELECT * FROM classes WHERE id=? AND flight_id=?",(cid,tid)).fetchone()
 if not t or not cl or not t["active"]: abort(404)
 if request.method=="POST":
  names=[x.strip() for x in request.form.getlist("passenger_name[]") if x.strip()]; ages=request.form.getlist("passenger_age[]")
  try: aa=[int(x) for x in ages]
  except: aa=[]
  mode=request.form.get("payment_mode","Online demo")
  if not names or len(names)>6 or len(names)!=len(ages) or len(aa)!=len(names) or any(a<1 or a>120 for a in aa): flash("Enter valid passenger names and ages (max 6).","danger")
  elif len(names)>available(tid,cl,t["journey_date"]): flash("Not enough seats are available.","danger")
  else:
   booking_code="".join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(10)); total=cl["fare"]*len(names)
   with db() as c:
    c.execute("INSERT INTO bookings(booking_code,user_id,flight_id,class_name,journey_date,passenger_names,passenger_ages,passenger_count,total_fare,status,payment_mode,payment_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(booking_code,me()["id"],tid,cl["class_name"],t["journey_date"]," | ".join(names)," | ".join(ages),len(names),total,"CONFIRMED",mode,"Demo payment successful" if mode=="Online demo" else "Demo offline payment recorded"))
   flash("Reservation confirmed. Save your BOOKING CODE: "+booking_code+". Demo payment only.","success"); return redirect(url_for("ticket",booking_code=booking_code))
 return render_template("book.html",t=t,cl=cl,available=available(tid,cl,t["journey_date"]))
@app.route("/ticket/<booking_code>")
@login_required
def ticket(booking_code):
 with db() as c: b=c.execute("SELECT b.*,t.number,t.name flight_name,t.origin,t.destination,t.departure,t.arrival FROM bookings b JOIN flights t ON t.id=b.flight_id WHERE booking_code=?",(booking_code.upper(),)).fetchone()
 if not b or (b["user_id"]!=me()["id"] and me()["role"]!="admin"): abort(404)
 return render_template("ticket.html",b=b)
@app.route("/booking_code",methods=["GET","POST"])
def booking_code():
 b=None
 if request.method=="POST":
  with db() as c: b=c.execute("SELECT b.*,t.number,t.name flight_name,t.origin,t.destination,t.departure,t.arrival FROM bookings b JOIN flights t ON t.id=b.flight_id WHERE booking_code=?",(request.form.get("booking_code","").strip().upper(),)).fetchone()
  if not b: flash("No reservation found for that BOOKING CODE.","danger")
 return render_template("booking_code.html",b=b)
@app.route("/my-reservations")
@login_required
def reservations():
 with db() as c: bs=c.execute("SELECT b.*,t.number,t.name flight_name,t.origin,t.destination,t.departure FROM bookings b JOIN flights t ON t.id=b.flight_id WHERE user_id=? ORDER BY b.created_at DESC",(me()["id"],)).fetchall()
 return render_template("reservations.html",bs=bs)
@app.route("/cancel",methods=["GET","POST"])
def cancel():
 if request.method=="POST":
  code=request.form.get("booking_code","").strip().upper()
  with db() as c: b=c.execute("SELECT * FROM bookings WHERE booking_code=?",(code,)).fetchone()
  if not b: flash("BOOKING CODE not found.","danger")
  elif b["status"]=="CANCELLED": flash("Already cancelled.","warning")
  elif not me() or (me()["id"]!=b["user_id"] and me()["role"]!="admin"): flash("Log in with the account that made this booking first.","warning"); return redirect(url_for("login"))
  else:
   pct=refund_pct(b["journey_date"]); amount=round(b["total_fare"]*pct/100,2)
   with db() as c: c.execute("UPDATE bookings SET status='CANCELLED',refund_amount=?,payment_status='Refund pending admin approval' WHERE booking_code=?",(amount,code))
   flash(f"Cancelled. Estimated refund ₹{amount:.2f} ({pct:.0f}%). Admin approval required; no money transferred.","success"); return redirect(url_for("reservations"))
 return render_template("cancel.html")
@app.route("/admin")
@admin_required
def admin():
 with db() as c:
  stats={"users":c.execute("SELECT COUNT(*) n FROM users WHERE role='passenger'").fetchone()["n"],"flights":c.execute("SELECT COUNT(*) n FROM flights").fetchone()["n"],"bookings":c.execute("SELECT COUNT(*) n FROM bookings").fetchone()["n"],"revenue":c.execute("SELECT COALESCE(SUM(total_fare),0) n FROM bookings WHERE status='CONFIRMED'").fetchone()["n"]}
  bs=c.execute("SELECT b.*,u.name passenger,t.name flight_name,t.number FROM bookings b JOIN users u ON u.id=b.user_id JOIN flights t ON t.id=b.flight_id ORDER BY b.created_at DESC LIMIT 8").fetchall()
 return render_template("admin/dashboard.html",stats=stats,bs=bs)
@app.route("/admin/flights",methods=["GET","POST"])
@admin_required
def admin_flights():
 if request.method=="POST":
  try:
   vals=[request.form[x].strip() for x in ("number","name","origin","destination")]; dep=request.form["departure"]; arr=request.form["arrival"]; d=date.fromisoformat(request.form["journey_date"]).isoformat(); zone=request.form.get("zone","Asia")
   if not all(vals) or vals[2].lower()==vals[3].lower(): raise ValueError
   with db() as c:
    c.execute("INSERT INTO flights(number,name,origin,destination,departure,arrival,journey_date,zone) VALUES(?,?,?,?,?,?,?,?)",(*vals,dep,arr,d,zone)); tid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    for name,cap,fare in zip(request.form.getlist("class_name[]"),request.form.getlist("capacity[]"),request.form.getlist("fare[]")):
     if name.strip(): c.execute("INSERT INTO classes(flight_id,class_name,capacity,fare) VALUES(?,?,?,?)",(tid,name.strip(),int(cap),float(fare)))
   flash("Flight and fares added.","success")
  except (ValueError,KeyError,sqlite3.IntegrityError): flash("Check flight fields, unique number, and fare/capacity values.","danger")
  return redirect(url_for("admin_flights"))
 with db() as c:
  ts=c.execute("SELECT * FROM flights ORDER BY journey_date,departure").fetchall()
  cm={t["id"]:c.execute("SELECT * FROM classes WHERE flight_id=? ORDER BY fare",(t["id"],)).fetchall() for t in ts}
 return render_template("admin/flights.html",ts=ts,cm=cm)
@app.route("/admin/flight/<int:tid>/toggle",methods=["POST"])
@admin_required
def toggle(tid):
 with db() as c:
  t=c.execute("SELECT active FROM flights WHERE id=?",(tid,)).fetchone()
  if not t: abort(404)
  c.execute("UPDATE flights SET active=? WHERE id=?",(0 if t["active"] else 1,tid))
 return redirect(url_for("admin_flights"))
@app.route("/admin/class/<int:cid>",methods=["POST"])
@admin_required
def edit_class(cid):
 try:
  cap=int(request.form["capacity"]); fare=float(request.form["fare"])
  if cap<1 or fare<0: raise ValueError
  with db() as c: c.execute("UPDATE classes SET capacity=?,fare=? WHERE id=?",(cap,fare,cid))
  flash("Class fare/capacity updated.","success")
 except: flash("Invalid capacity or fare.","danger")
 return redirect(url_for("admin_flights"))
@app.route("/admin/bookings")
@admin_required
def admin_bookings():
 with db() as c: bs=c.execute("SELECT b.*,u.name passenger,u.email,t.name flight_name,t.number FROM bookings b JOIN users u ON u.id=b.user_id JOIN flights t ON t.id=b.flight_id ORDER BY b.created_at DESC").fetchall()
 return render_template("admin/bookings.html",bs=bs)
@app.route("/admin/refund/<booking_code>",methods=["POST"])
@admin_required
def refund(booking_code):
 with db() as c:
  b=c.execute("SELECT * FROM bookings WHERE booking_code=?",(booking_code,)).fetchone()
  if not b: abort(404)
  if b["status"]!="CANCELLED": flash("Only cancelled tickets can be refunded.","danger")
  else: c.execute("UPDATE bookings SET payment_status='Refund marked processed' WHERE booking_code=?",(booking_code,)); flash("Refund marked processed for lab records only; no money transferred.","success")
 return redirect(url_for("admin_bookings"))
@app.route("/admin/users")
@admin_required
def admin_users():
 with db() as c: us=c.execute("SELECT u.id,u.name,u.email,u.role,u.created_at,COUNT(b.id) bookings FROM users u LEFT JOIN bookings b ON b.user_id=u.id GROUP BY u.id ORDER BY u.created_at DESC").fetchall()
 return render_template("admin/users.html",us=us)
@app.route("/admin/refund-rules",methods=["GET","POST"])
@admin_required
def rules():
 if request.method=="POST":
  try:
   label=request.form["label"].strip(); lo=int(request.form["min_days"]); hi=int(request.form["max_days"]); pct=float(request.form["percent"])
   if not label or lo<0 or hi<lo or pct<0 or pct>100: raise ValueError
   with db() as c: c.execute("INSERT INTO refund_rules(min_days,max_days,refund_percent,label) VALUES(?,?,?,?)",(lo,hi,pct,label))
   flash("Refund rule added.","success")
  except: flash("Check refund rule fields.","danger")
  return redirect(url_for("rules"))
 with db() as c: rs=c.execute("SELECT * FROM refund_rules ORDER BY min_days DESC").fetchall()
 return render_template("admin/rules.html",rs=rs)
@app.route("/admin/reports")
@admin_required
def reports():
 with db() as c:
  summary=c.execute("SELECT COUNT(*) total,SUM(status='CONFIRMED') confirmed,SUM(status='CANCELLED') cancelled,COALESCE(SUM(CASE WHEN status='CONFIRMED' THEN total_fare ELSE 0 END),0) revenue,COALESCE(SUM(CASE WHEN status='CANCELLED' THEN refund_amount ELSE 0 END),0) refunds FROM bookings").fetchone()
  rows=c.execute("SELECT t.number,t.name,t.origin,t.destination,COUNT(b.id) bookings,COALESCE(SUM(CASE WHEN b.status='CONFIRMED' THEN b.total_fare ELSE 0 END),0) revenue FROM flights t LEFT JOIN bookings b ON b.flight_id=t.id GROUP BY t.id ORDER BY bookings DESC").fetchall()
 feedback_rows=c.execute("SELECT f.*,u.name,u.email FROM feedback f JOIN users u ON u.id=f.user_id ORDER BY f.created_at DESC").fetchall()
 return render_template("admin/reports.html",s=summary,rows=rows,feedback_rows=feedback_rows)
@app.route("/admin/reports.csv")
@admin_required
def csv_report():
 with db() as c: rows=c.execute("SELECT b.booking_code,u.name,u.email,t.number,t.name,b.journey_date,b.class_name,b.passenger_names,b.passenger_count,b.total_fare,b.status,b.payment_mode,b.payment_status,b.refund_amount FROM bookings b JOIN users u ON u.id=b.user_id JOIN flights t ON t.id=b.flight_id ORDER BY b.created_at DESC").fetchall()
 out=io.StringIO(); w=csv.writer(out); w.writerow(["BOOKING CODE","Account","Email","Flight no","Flight","Date","Class","Passengers","Count","Fare","Status","Payment mode","Payment status","Refund"])
 for r in rows: w.writerow(list(r))
 res=make_response(out.getvalue()); res.headers["Content-Type"]="text/csv; charset=utf-8"; res.headers["Content-Disposition"]="attachment; filename=aerovista_flight_report.csv"; return res
@app.errorhandler(404)
def nf(e): return render_template("404.html"),404
if __name__=="__main__": init_db(); app.run(debug=True,port=5000)
