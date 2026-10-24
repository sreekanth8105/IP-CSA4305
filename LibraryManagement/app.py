from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, timedelta, datetime

app = Flask(__name__)
app.secret_key = "libra-library-secret-key"


# =========================================================
# USERS
# =========================================================

users = [
    {
        "id": 1,
        "name": "Admin",
        "email": "admin@libra.com",
        "password": "admin123",
        "role": "admin"
    },
    {
        "id": 2,
        "name": "Sumanth",
        "email": "student@libra.com",
        "password": "student123",
        "role": "student"
    }
]


# =========================================================
# BOOKS
# =========================================================

books = [
    {
        "id": 1,
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "category": "Software Engineering",
        "year": 2008,
        "quantity": 5,
        "available": 5
    },
    {
        "id": 2,
        "title": "The Pragmatic Programmer",
        "author": "David Thomas & Andrew Hunt",
        "category": "Programming",
        "year": 2019,
        "quantity": 4,
        "available": 4
    },
    {
        "id": 3,
        "title": "Introduction to Algorithms",
        "author": "Thomas H. Cormen",
        "category": "Algorithms",
        "year": 2022,
        "quantity": 6,
        "available": 6
    },
    {
        "id": 4,
        "title": "Python Crash Course",
        "author": "Eric Matthes",
        "category": "Python",
        "year": 2023,
        "quantity": 5,
        "available": 5
    },
    {
        "id": 5,
        "title": "Database System Concepts",
        "author": "Abraham Silberschatz",
        "category": "Database",
        "year": 2020,
        "quantity": 4,
        "available": 4
    },
    {
        "id": 6,
        "title": "Computer Networks",
        "author": "Andrew S. Tanenbaum",
        "category": "Networking",
        "year": 2021,
        "quantity": 5,
        "available": 5
    },
    {
        "id": 7,
        "title": "Operating System Concepts",
        "author": "Abraham Silberschatz",
        "category": "Operating Systems",
        "year": 2018,
        "quantity": 4,
        "available": 4
    },
    {
        "id": 8,
        "title": "Artificial Intelligence: A Modern Approach",
        "author": "Stuart Russell & Peter Norvig",
        "category": "Artificial Intelligence",
        "year": 2021,
        "quantity": 3,
        "available": 3
    },
    {
        "id": 9,
        "title": "Head First Java",
        "author": "Kathy Sierra & Bert Bates",
        "category": "Java",
        "year": 2022,
        "quantity": 4,
        "available": 4
    },
    {
        "id": 10,
        "title": "Design Patterns",
        "author": "Erich Gamma",
        "category": "Software Design",
        "year": 2019,
        "quantity": 3,
        "available": 3
    }
]


# =========================================================
# BORROW RECORDS
# =========================================================

borrow_records = []


# =========================================================
# BOOK REQUESTS
# =========================================================
#
# Student requests a book.
# Admin later approves/issues the request.
#

book_requests = []


# =========================================================
# STUDY MATERIALS
# =========================================================

materials = [
    {
        "id": 1,
        "title": "Data Structures and Algorithms Notes",
        "subject": "Data Structures",
        "type": "Notes",
        "link": "#"
    },
    {
        "id": 2,
        "title": "Database Management Systems",
        "subject": "DBMS",
        "type": "Study Material",
        "link": "#"
    },
    {
        "id": 3,
        "title": "Computer Networks Reference Material",
        "subject": "Computer Networks",
        "type": "Reference",
        "link": "#"
    },
    {
        "id": 4,
        "title": "Operating Systems Quick Revision",
        "subject": "Operating Systems",
        "type": "Notes",
        "link": "#"
    },
    {
        "id": 5,
        "title": "Python Programming Guide",
        "subject": "Python",
        "type": "Study Material",
        "link": "#"
    },
    {
        "id": 6,
        "title": "Machine Learning Fundamentals",
        "subject": "Machine Learning",
        "type": "Reference",
        "link": "#"
    },
    {
        "id": 7,
        "title": "Web Technologies Notes",
        "subject": "Internet Programming",
        "type": "Notes",
        "link": "#"
    },
    {
        "id": 8,
        "title": "Software Engineering Guide",
        "subject": "Software Engineering",
        "type": "Study Material",
        "link": "#"
    }
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_current_user():

    user_id = session.get("user_id")

    if user_id is None:
        return None

    for user in users:

        if user["id"] == user_id:
            return user

    return None


def is_admin():

    user = get_current_user()

    return user is not None and user["role"] == "admin"


def is_student():

    user = get_current_user()

    return user is not None and user["role"] == "student"


def get_book(book_id):

    for book in books:

        if book["id"] == book_id:
            return book

    return None


def get_student(student_id):

    for user in users:

        if (
            user["id"] == student_id
            and user["role"] == "student"
        ):
            return user

    return None


def next_book_id():

    if not books:
        return 1

    return max(
        book["id"]
        for book in books
    ) + 1


def next_borrow_id():

    if not borrow_records:
        return 1

    return max(
        record["id"]
        for record in borrow_records
    ) + 1


def next_request_id():

    if not book_requests:
        return 1

    return max(
        req["id"]
        for req in book_requests
    ) + 1


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    user = get_current_user()

    if user:

        if user["role"] == "admin":
            return redirect(
                url_for("admin_dashboard")
            )

        return redirect(
            url_for("student_dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            ""
        )

        for user in users:

            if (
                user["email"].lower() == email.lower()
                and user["password"] == password
                and user["role"] == role
            ):

                session.clear()

                session["user_id"] = user["id"]

                if user["role"] == "admin":

                    return redirect(
                        url_for("admin_dashboard")
                    )

                return redirect(
                    url_for("student_dashboard")
                )

        flash(
            "Invalid email, password, or account type.",
            "error"
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student")
def student_dashboard():

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    student_records = [
        record
        for record in borrow_records
        if record["user_id"] == user["id"]
    ]

    student_requests = [
        req
        for req in book_requests
        if req["user_id"] == user["id"]
    ]

    borrowed_count = len([
        record
        for record in student_records
        if record["status"] == "Issued"
    ])

    pending_count = len([
        req
        for req in student_requests
        if req["status"] == "Pending"
    ])

    total_fine = sum(
        record["fine"]
        for record in student_records
    )

    available_copies = sum(
        book["available"]
        for book in books
    )

    return render_template(
        "student_dashboard.html",
        user=user,
        borrowed_count=borrowed_count,
        pending_count=pending_count,
        total_fine=total_fine,
        available_copies=available_copies,
        books=books
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin_dashboard():

    if not is_admin():
        return redirect(url_for("login"))

    total_books = sum(
        book["quantity"]
        for book in books
    )

    available_books = sum(
        book["available"]
        for book in books
    )

    issued_books = len([
        record
        for record in borrow_records
        if record["status"] == "Issued"
    ])

    total_fines = sum(
        record["fine"]
        for record in borrow_records
    )

    pending_requests = [
        req
        for req in book_requests
        if req["status"] == "Pending"
    ]

    return render_template(
        "admin_dashboard.html",
        total_books=total_books,
        available_books=available_books,
        issued_books=issued_books,
        total_fines=total_fines,
        books=books,
        records=borrow_records,
        pending_requests=pending_requests
    )


# =========================================================
# BOOK CATALOG
# =========================================================

@app.route("/books")
def book_catalog():

    if not get_current_user():
        return redirect(url_for("login"))

    search = request.args.get(
        "search",
        ""
    ).strip().lower()

    if search:

        filtered_books = [
            book
            for book in books
            if (
                search in book["title"].lower()
                or search in book["author"].lower()
                or search in book["category"].lower()
            )
        ]

    else:

        filtered_books = books

    return render_template(
        "books.html",
        books=filtered_books,
        search=search
    )


# =========================================================
# STUDENT - REQUEST BOOK
# =========================================================

@app.route(
    "/request-book/<int:book_id>",
    methods=["POST"]
)
def request_book(book_id):

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    book = get_book(book_id)

    if book is None:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("book_catalog")
        )

    if book["available"] <= 0:

        flash(
            "This book is currently unavailable.",
            "error"
        )

        return redirect(
            url_for("book_catalog")
        )

    # Check whether student already has the book.

    already_issued = any(
        record["user_id"] == user["id"]
        and record["book_id"] == book_id
        and record["status"] == "Issued"
        for record in borrow_records
    )

    if already_issued:

        flash(
            "You already have this book.",
            "error"
        )

        return redirect(
            url_for("book_catalog")
        )

    # Check whether request already exists.

    already_requested = any(
        req["user_id"] == user["id"]
        and req["book_id"] == book_id
        and req["status"] == "Pending"
        for req in book_requests
    )

    if already_requested:

        flash(
            "This book is already in your request list.",
            "error"
        )

        return redirect(
            url_for("book_catalog")
        )

    new_request = {
        "id": next_request_id(),
        "user_id": user["id"],
        "student_name": user["name"],
        "book_id": book["id"],
        "book_title": book["title"],
        "request_date": date.today().strftime(
            "%d-%m-%Y"
        ),
        "status": "Pending"
    }

    book_requests.append(new_request)

    flash(
        f'"{book["title"]}" has been added to your request list.',
        "success"
    )

    return redirect(
        url_for("book_catalog")
    )


# =========================================================
# STUDENT - REQUEST CART
# =========================================================

@app.route("/cart")
def request_cart():

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    requests = [
        req
        for req in book_requests
        if req["user_id"] == user["id"]
    ]

    return render_template(
        "cart.html",
        requests=requests
    )


# =========================================================
# STUDENT - REMOVE PENDING REQUEST
# =========================================================

@app.route(
    "/cart/remove/<int:request_id>"
)
def remove_request(request_id):

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    selected_request = next(
        (
            req
            for req in book_requests
            if (
                req["id"] == request_id
                and req["user_id"] == user["id"]
            )
        ),
        None
    )

    if selected_request is None:

        flash(
            "Request not found.",
            "error"
        )

        return redirect(
            url_for("request_cart")
        )

    if selected_request["status"] != "Pending":

        flash(
            "Only pending requests can be removed.",
            "error"
        )

        return redirect(
            url_for("request_cart")
        )

    book_requests.remove(
        selected_request
    )

    flash(
        "Book request removed.",
        "success"
    )

    return redirect(
        url_for("request_cart")
    )


# =========================================================
# STUDENT - BORROW HISTORY
# =========================================================

@app.route("/borrow-history")
def borrow_history():

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    records = [
        record
        for record in borrow_records
        if record["user_id"] == user["id"]
    ]

    return render_template(
        "borrow_history.html",
        records=records
    )


# =========================================================
# STUDY MATERIALS
# =========================================================

@app.route("/materials")
def view_materials():

    if not get_current_user():
        return redirect(url_for("login"))

    search = request.args.get(
        "search",
        ""
    ).strip().lower()

    if search:

        filtered_materials = [
            material
            for material in materials
            if (
                search in material["title"].lower()
                or search in material["subject"].lower()
                or search in material["type"].lower()
            )
        ]

    else:

        filtered_materials = materials

    return render_template(
        "materials.html",
        materials=filtered_materials,
        search=search
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if not is_student():
        return redirect(url_for("login"))

    user = get_current_user()

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# ADMIN - MANAGE BOOKS
# =========================================================

@app.route(
    "/admin/books",
    methods=["GET", "POST"]
)
def manage_books():

    if not is_admin():
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        author = request.form.get(
            "author",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        year = request.form.get(
            "year",
            ""
        ).strip()

        quantity = request.form.get(
            "quantity",
            ""
        ).strip()

        if not all([
            title,
            author,
            category,
            year,
            quantity
        ]):

            flash(
                "Please fill in all book details.",
                "error"
            )

            return redirect(
                url_for("manage_books")
            )

        try:

            year = int(year)
            quantity = int(quantity)

        except ValueError:

            flash(
                "Year and quantity must be numbers.",
                "error"
            )

            return redirect(
                url_for("manage_books")
            )

        if quantity <= 0:

            flash(
                "Quantity must be at least 1.",
                "error"
            )

            return redirect(
                url_for("manage_books")
            )

        new_book = {
            "id": next_book_id(),
            "title": title,
            "author": author,
            "category": category,
            "year": year,
            "quantity": quantity,
            "available": quantity
        }

        books.append(new_book)

        flash(
            f'"{title}" was added successfully.',
            "success"
        )

        return redirect(
            url_for("manage_books")
        )

    return render_template(
        "manage_books.html",
        books=books
    )


# =========================================================
# ADMIN - DELETE BOOK
# =========================================================

@app.route(
    "/admin/books/delete/<int:book_id>"
)
def delete_book(book_id):

    if not is_admin():
        return redirect(url_for("login"))

    book = get_book(book_id)

    if book is None:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("manage_books")
        )

    issued_count = len([
        record
        for record in borrow_records
        if (
            record["book_id"] == book_id
            and record["status"] == "Issued"
        )
    ])

    if issued_count > 0:

        flash(
            "This book cannot be deleted while it is issued.",
            "error"
        )

        return redirect(
            url_for("manage_books")
        )

    books.remove(book)

    flash(
        f'"{book["title"]}" was deleted successfully.',
        "success"
    )

    return redirect(
        url_for("manage_books")
    )


# =========================================================
# ADMIN - UPDATE BOOK
# =========================================================

@app.route(
    "/admin/books/update/<int:book_id>",
    methods=["POST"]
)
def update_book(book_id):

    if not is_admin():
        return redirect(url_for("login"))

    book = get_book(book_id)

    if book is None:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("manage_books")
        )

    title = request.form.get(
        "title",
        ""
    ).strip()

    author = request.form.get(
        "author",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    year = request.form.get(
        "year",
        ""
    ).strip()

    quantity = request.form.get(
        "quantity",
        ""
    ).strip()

    try:

        year = int(year)
        quantity = int(quantity)

    except ValueError:

        flash(
            "Year and quantity must be numbers.",
            "error"
        )

        return redirect(
            url_for("manage_books")
        )

    issued_copies = (
        book["quantity"] -
        book["available"]
    )

    if quantity < issued_copies:

        flash(
            "Quantity cannot be lower than currently issued copies.",
            "error"
        )

        return redirect(
            url_for("manage_books")
        )

    book["title"] = title
    book["author"] = author
    book["category"] = category
    book["year"] = year
    book["quantity"] = quantity
    book["available"] = quantity - issued_copies

    flash(
        f'"{title}" was updated successfully.',
        "success"
    )

    return redirect(
        url_for("manage_books")
    )


# =========================================================
# ADMIN - ISSUE REQUESTED BOOK
# =========================================================

@app.route(
    "/admin/request/<int:request_id>/issue"
)
def approve_book_request(request_id):

    if not is_admin():
        return redirect(url_for("login"))

    selected_request = next(
        (
            req
            for req in book_requests
            if req["id"] == request_id
        ),
        None
    )

    if selected_request is None:

        flash(
            "Book request not found.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    if selected_request["status"] != "Pending":

        flash(
            "This request has already been processed.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    book = get_book(
        selected_request["book_id"]
    )

    student = get_student(
        selected_request["user_id"]
    )

    if book is None or student is None:

        flash(
            "Book or student information is missing.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    if book["available"] <= 0:

        flash(
            "This book is no longer available.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    # Make sure the student doesn't already have it.

    already_issued = any(
        record["user_id"] == student["id"]
        and record["book_id"] == book["id"]
        and record["status"] == "Issued"
        for record in borrow_records
    )

    if already_issued:

        selected_request["status"] = "Rejected"

        flash(
            "Student already has this book issued.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    issue_date = date.today()

    expected_date = (
        issue_date +
        timedelta(days=14)
    )

    new_record = {
        "id": next_borrow_id(),
        "user_id": student["id"],
        "student_name": student["name"],
        "book_id": book["id"],
        "book_title": book["title"],
        "issue_date": issue_date.strftime(
            "%d-%m-%Y"
        ),
        "expected_date": expected_date.strftime(
            "%d-%m-%Y"
        ),
        "return_date": "-",
        "status": "Issued",
        "fine": 0
    }

    borrow_records.append(
        new_record
    )

    book["available"] -= 1

    selected_request["status"] = "Issued"

    flash(
        f'"{book["title"]}" has been issued to '
        f'{student["name"]}.',
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN - REJECT REQUEST
# =========================================================

@app.route(
    "/admin/request/<int:request_id>/reject"
)
def reject_book_request(request_id):

    if not is_admin():
        return redirect(url_for("login"))

    selected_request = next(
        (
            req
            for req in book_requests
            if req["id"] == request_id
        ),
        None
    )

    if selected_request is None:

        flash(
            "Book request not found.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    if selected_request["status"] != "Pending":

        flash(
            "This request has already been processed.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    selected_request["status"] = "Rejected"

    flash(
        "Book request rejected.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN - RETURN BOOK
# =========================================================

@app.route(
    "/admin/return/<int:record_id>"
)
def return_book(record_id):

    if not is_admin():
        return redirect(url_for("login"))

    record = next(
        (
            item
            for item in borrow_records
            if item["id"] == record_id
        ),
        None
    )

    if record is None:

        flash(
            "Borrowing record not found.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    if record["status"] != "Issued":

        flash(
            "This book has already been returned.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    issue_date = datetime.strptime(
        record["issue_date"],
        "%d-%m-%Y"
    ).date()

    today = date.today()

    days_used = (
        today - issue_date
    ).days

    # 14 days allowed.
    # ₹5 per late day.

    if days_used > 14:

        late_days = days_used - 14

        record["fine"] = late_days * 5

    else:

        record["fine"] = 0

    record["return_date"] = today.strftime(
        "%d-%m-%Y"
    )

    record["status"] = "Returned"

    book = get_book(
        record["book_id"]
    )

    if book:

        book["available"] = min(
            book["available"] + 1,
            book["quantity"]
        )

    flash(
        f'"{record["book_title"]}" returned successfully.',
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN - FINE MANAGEMENT
# =========================================================

@app.route("/admin/fines")
def fines():

    if not is_admin():
        return redirect(url_for("login"))

    total_fines = sum(
        record["fine"]
        for record in borrow_records
    )

    total_books = sum(
        book["quantity"]
        for book in books
    )

    available_books = sum(
        book["available"]
        for book in books
    )

    issued_books = len([
        record
        for record in borrow_records
        if record["status"] == "Issued"
    ])

    pending_requests = [
        req
        for req in book_requests
        if req["status"] == "Pending"
    ]

    return render_template(
        "admin_dashboard.html",
        total_fines=total_fines,
        total_books=total_books,
        available_books=available_books,
        issued_books=issued_books,
        books=books,
        records=borrow_records,
        pending_requests=pending_requests
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )