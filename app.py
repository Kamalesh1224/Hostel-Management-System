from datetime import datetime
from functools import wraps
import os
import re
import sqlite3

from flask import Flask, flash, g, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["DATABASE"] = os.path.join(app.root_path, "hostel_complaints.db")

ALLOWED_CATEGORIES = [
    "Electrical Fault",
    "Room Related",
    "Food",
    "Water",
    "Bathroom",
]
ALLOWED_STATUSES = ["Pending", "In Progress", "Resolved"]
ALLOWED_PRIORITIES = ["Low", "Medium", "High"]
MAX_ACTIVE_COMPLAINTS = 5
MAX_DESCRIPTION_LENGTH = 500
COLLEGE_NAME = "Tagore Engineering College"
COLLEGE_SYSTEM_NAME = "Hostel Complaint Management System"
COLLEGE_LOGO_URL = "https://tagore-engg.ac.in/images/tagore-logo.png"


STYLE = """
:root {
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #1a202c;
  --muted: #4a5568;
  --primary: #0f4c81;
  --success: #0f7a4f;
  --border: #d9e2ec;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(180deg, #eef3fb 0%, #f8fafc 100%);
  color: var(--text);
}
.container {
  max-width: 1000px;
  margin: 24px auto;
  padding: 0 16px;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 6px rgba(15, 76, 129, 0.08);
}
h1, h2, h3 { margin-top: 0; }
label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}
input, select, textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #b9c6d3;
  border-radius: 8px;
  margin-bottom: 12px;
  font: inherit;
}
textarea { min-height: 90px; resize: vertical; }
button, .btn {
  display: inline-block;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  text-decoration: none;
  font-weight: 600;
}
.btn-secondary {
  background: #4a5568;
}
.btn-success {
  background: var(--success);
}
.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.nav {
  background: #102a43;
  color: #fff;
  padding: 12px 16px;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.nav a {
  color: #fff;
  text-decoration: none;
  margin-right: 12px;
  font-weight: 600;
}
.nav-title {
  font-weight: 700;
}
.brand-header {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0;
  margin-bottom: 16px;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  gap: 0;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(15, 76, 129, 0.06);
}
.brand-logo {
  width: 100%;
  height: auto;
  display: block;
  object-fit: cover;
  border-radius: 0;
  background: #fff;
}
.brand-title {
  margin: 0;
  font-size: 1.2rem;
}
.brand-subtitle {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}
.alert {
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 12px;
  border: 1px solid #b7d7c9;
  background: #e8f6ee;
  color: #1e5631;
}
.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid var(--border);
  padding: 10px;
  text-align: left;
  vertical-align: top;
}
th { background: #eef3fb; }
.small { color: var(--muted); font-size: 0.9rem; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.status-pending { color: #a16207; font-weight: 700; }
.status-inprogress { color: #1d4ed8; font-weight: 700; }
.status-resolved { color: #166534; font-weight: 700; }
.priority-low { color: #166534; font-weight: 700; }
.priority-medium { color: #a16207; font-weight: 700; }
.priority-high { color: #b91c1c; font-weight: 700; }
.chip {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef3fb;
  border: 1px solid #d9e2ec;
  font-size: 0.86rem;
  margin-right: 6px;
}
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT NOT NULL,
            hostel_block TEXT NOT NULL,
            room_number TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            staff_assigned TEXT,
            remarks TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        """
    )
    # Keep existing databases compatible when new fields are introduced.
    for statement in [
        "ALTER TABLE complaints ADD COLUMN hostel_block TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE complaints ADD COLUMN room_number TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE complaints ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'",
        "ALTER TABLE complaints ADD COLUMN updated_at TEXT",
    ]:
        try:
            db.execute(statement)
        except sqlite3.OperationalError:
            pass
    db.commit()


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("student_roll"):
            return redirect(url_for("student_login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def status_class(status):
    if status == "Pending":
        return "status-pending"
    if status == "In Progress":
        return "status-inprogress"
    return "status-resolved"


def priority_class(priority):
    if priority == "High":
        return "priority-high"
    if priority == "Medium":
        return "priority-medium"
    return "priority-low"


app.jinja_env.globals.update(
    status_class=status_class,
    priority_class=priority_class,
    college_name=COLLEGE_NAME,
    college_system_name=COLLEGE_SYSTEM_NAME,
    college_logo_url=COLLEGE_LOGO_URL,
)


@app.route("/")
def index():
    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Hostel Portal</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <span class="nav-title">Portal</span>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card">
              <h2>Welcome</h2>
              <p class="small">Students can raise complaints and track status. Admin can manage all complaints.</p>
              <a class="btn" href="{{ url_for('student_login') }}">Student Login</a>
              <a class="btn btn-secondary" href="{{ url_for('admin_login') }}">Admin Login</a>
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
    )


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        if not re.fullmatch(r"4127\d+", roll_number):
            flash("Enter a valid roll number that starts with 4127 and contains only digits.")
        else:
            session.pop("admin_id", None)
            session["student_roll"] = roll_number
            return redirect(url_for("student_dashboard"))

    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Student Login</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <a href="{{ url_for('index') }}">Home</a>
            <span class="nav-title">Student Portal</span>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card" style="max-width:520px;">
              <h2>Student Login</h2>
              <p class="small">Use your unique roll number (must start with 4127).</p>
              {% with messages = get_flashed_messages() %}
                {% if messages %}
                  {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                  {% endfor %}
                {% endif %}
              {% endwith %}
              <form method="post">
                <label for="roll_number">Roll Number</label>
                <input id="roll_number" name="roll_number" type="text" required placeholder="4127...">
                <button type="submit">Login</button>
              </form>
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
    )


@app.route("/student/dashboard", methods=["GET", "POST"])
@student_required
def student_dashboard():
    db = get_db()
    roll_number = session["student_roll"]

    if request.method == "POST":
        hostel_block = request.form.get("hostel_block", "").strip()
        room_number = request.form.get("room_number", "").strip().upper()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "").strip()
        description = request.form.get("description", "").strip()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if category not in ALLOWED_CATEGORIES:
            flash("Please select a valid complaint category.")
        elif priority not in ALLOWED_PRIORITIES:
            flash("Please select a valid priority.")
        elif not hostel_block:
            flash("Hostel block is required.")
        elif len(hostel_block) > 30:
            flash("Hostel block must be 30 characters or less.")
        elif not room_number:
            flash("Room number is required.")
        elif not re.fullmatch(r"[A-Za-z0-9/-]{1,20}", room_number):
            flash("Room number can contain letters, numbers, '-' or '/'.")
        elif not description:
            flash("Complaint description is required.")
        elif len(description) < 10:
            flash("Complaint description must be at least 10 characters.")
        elif len(description) > MAX_DESCRIPTION_LENGTH:
            flash(f"Complaint description must be under {MAX_DESCRIPTION_LENGTH} characters.")
        else:
            active_count = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM complaints
                WHERE roll_number = ? AND status IN ('Pending', 'In Progress')
                """,
                (roll_number,),
            ).fetchone()["total"]
            if active_count >= MAX_ACTIVE_COMPLAINTS:
                flash(
                    f"You already have {MAX_ACTIVE_COMPLAINTS} active complaints. "
                    "Please wait for resolution before filing new ones."
                )
                return redirect(url_for("student_dashboard"))
            db.execute(
                """
                INSERT INTO complaints (
                    roll_number, hostel_block, room_number, category, priority,
                    description, status, staff_assigned, remarks, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'Pending', '', '', ?, ?)
                """,
                (
                    roll_number,
                    hostel_block,
                    room_number,
                    category,
                    priority,
                    description,
                    current_time,
                    current_time,
                ),
            )
            db.commit()
            flash("Complaint submitted successfully.")
            return redirect(url_for("student_dashboard"))

    complaints = db.execute(
        """
        SELECT id, hostel_block, room_number, category, priority, description, status,
               staff_assigned, remarks, created_at, updated_at
        FROM complaints
        WHERE roll_number = ?
        ORDER BY id DESC
        """,
        (roll_number,),
    ).fetchall()

    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Student Dashboard</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <a href="{{ url_for('index') }}">Home</a>
            <span class="nav-title">Student Portal</span>
            <a href="{{ url_for('student_logout') }}">Logout</a>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card">
              <h2>Welcome, {{ roll_number }}</h2>
              <p class="small">File complaints and track status/history. Maximum active complaints allowed: {{ max_active }}.</p>
            </div>

            <div class="grid">
              <div class="card">
                <h3>File New Complaint</h3>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    {% for message in messages %}
                      <div class="alert">{{ message }}</div>
                    {% endfor %}
                  {% endif %}
                {% endwith %}
                <form method="post">
                  <label for="hostel_block">Hostel Block</label>
                  <input id="hostel_block" name="hostel_block" type="text" required maxlength="30" placeholder="e.g. A Block">

                  <label for="room_number">Room Number</label>
                  <input id="room_number" name="room_number" type="text" required maxlength="20" placeholder="e.g. 102 or B-204">

                  <label for="category">Category</label>
                  <select id="category" name="category" required>
                    <option value="">Select category</option>
                    {% for item in categories %}
                      <option value="{{ item }}">{{ item }}</option>
                    {% endfor %}
                  </select>

                  <label for="priority">Priority</label>
                  <select id="priority" name="priority" required>
                    <option value="">Select priority</option>
                    {% for item in priorities %}
                      <option value="{{ item }}">{{ item }}</option>
                    {% endfor %}
                  </select>

                  <label for="description">Complaint Details</label>
                  <textarea id="description" name="description" required maxlength="{{ max_description }}" placeholder="Explain the issue clearly (10 to {{ max_description }} characters)"></textarea>

                  <button class="btn btn-success" type="submit">Submit Complaint</button>
                </form>
              </div>

              <div class="card">
                <h3>Your Complaint History</h3>
                {% if complaints %}
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Block</th>
                        <th>Room</th>
                        <th>Category</th>
                        <th>Priority</th>
                        <th>Description</th>
                        <th>Status</th>
                        <th>Assigned Staff</th>
                        <th>Admin Remarks</th>
                        <th>Created</th>
                        <th>Last Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                    {% for row in complaints %}
                      <tr>
                        <td>{{ row['id'] }}</td>
                        <td>{{ row['hostel_block'] }}</td>
                        <td>{{ row['room_number'] }}</td>
                        <td>{{ row['category'] }}</td>
                        <td class="{{ priority_class(row['priority']) }}">{{ row['priority'] }}</td>
                        <td>{{ row['description'] }}</td>
                        <td class="{{ status_class(row['status']) }}">{{ row['status'] }}</td>
                        <td>{{ row['staff_assigned'] or '-' }}</td>
                        <td>{{ row['remarks'] or '-' }}</td>
                        <td>{{ row['created_at'] }}</td>
                        <td>{{ row['updated_at'] or row['created_at'] }}</td>
                      </tr>
                    {% endfor %}
                    </tbody>
                  </table>
                </div>
                {% else %}
                  <p class="small">No complaints filed yet.</p>
                {% endif %}
              </div>
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
        roll_number=roll_number,
        categories=ALLOWED_CATEGORIES,
        priorities=ALLOWED_PRIORITIES,
        max_active=MAX_ACTIVE_COMPLAINTS,
        max_description=MAX_DESCRIPTION_LENGTH,
        complaints=complaints,
    )


@app.route("/student/logout")
def student_logout():
    session.pop("student_roll", None)
    flash("Student logged out.")
    return redirect(url_for("student_login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        if not admin or not check_password_hash(admin["password_hash"], password):
            flash("Invalid admin username or password.")
        else:
            session.pop("student_roll", None)
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))

    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Admin Login</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <a href="{{ url_for('index') }}">Home</a>
            <span class="nav-title">Admin Portal</span>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card" style="max-width:520px;">
              <h2>Admin Login</h2>
              <p class="small">Login using admin username and password.</p>
              {% with messages = get_flashed_messages() %}
                {% if messages %}
                  {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                  {% endfor %}
                {% endif %}
              {% endwith %}
              <form method="post">
                <label for="username">Username</label>
                <input id="username" name="username" type="text" required>

                <label for="password">Password</label>
                <input id="password" name="password" type="password" required>

                <div class="action-row">
                  <button type="submit">Login</button>
                  <a class="btn btn-secondary" href="{{ url_for('admin_register') }}">Create Admin</a>
                </div>
              </form>
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
    )


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("Admin username must be at least 3 characters.")
        elif len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            flash("Admin password must be at least 8 characters and include letters and numbers.")
        else:
            try:
                db.execute(
                    "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (
                        username,
                        generate_password_hash(password),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                db.commit()
                flash("Admin account created. Please login.")
                return redirect(url_for("admin_login"))
            except sqlite3.IntegrityError:
                flash("This admin username already exists.")

    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Create Admin</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <a href="{{ url_for('index') }}">Home</a>
            <a href="{{ url_for('admin_login') }}">Admin Login</a>
            <span class="nav-title">Create Admin</span>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card" style="max-width:520px;">
              <h2>Create Admin Account</h2>
              {% with messages = get_flashed_messages() %}
                {% if messages %}
                  {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                  {% endfor %}
                {% endif %}
              {% endwith %}
              <form method="post">
                <label for="username">Admin Username</label>
                <input id="username" name="username" type="text" required>

                <label for="password">Admin Password</label>
                <input id="password" name="password" type="password" required>

                <button type="submit">Create Admin</button>
              </form>
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
    )


@app.route("/admin/dashboard", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    db = get_db()

    status_filter = request.values.get("status_filter", "All").strip()
    category_filter = request.values.get("category_filter", "All").strip()
    priority_filter = request.values.get("priority_filter", "All").strip()

    if request.method == "POST":
        complaint_id = request.form.get("complaint_id", "").strip()
        status = request.form.get("status", "").strip()
        priority = request.form.get("priority", "").strip()
        staff_assigned = request.form.get("staff_assigned", "").strip()
        remarks = request.form.get("remarks", "").strip()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not complaint_id.isdigit():
            flash("Invalid complaint ID.")
        elif status not in ALLOWED_STATUSES:
            flash("Invalid status selected.")
        elif priority not in ALLOWED_PRIORITIES:
            flash("Invalid priority selected.")
        else:
            db.execute(
                """
                UPDATE complaints
                SET status = ?, priority = ?, staff_assigned = ?, remarks = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, priority, staff_assigned, remarks, current_time, int(complaint_id)),
            )
            db.commit()
            flash(f"Complaint #{complaint_id} updated.")
            return redirect(
                url_for(
                    "admin_dashboard",
                    status_filter=status_filter,
                    category_filter=category_filter,
                    priority_filter=priority_filter,
                )
            )

    where_clauses = []
    params = []
    if status_filter in ALLOWED_STATUSES:
        where_clauses.append("status = ?")
        params.append(status_filter)
    else:
        status_filter = "All"

    if category_filter in ALLOWED_CATEGORIES:
        where_clauses.append("category = ?")
        params.append(category_filter)
    else:
        category_filter = "All"

    if priority_filter in ALLOWED_PRIORITIES:
        where_clauses.append("priority = ?")
        params.append(priority_filter)
    else:
        priority_filter = "All"

    base_query = """
        SELECT id, hostel_block, room_number, category, priority, description, status,
               staff_assigned, remarks, created_at, updated_at
        FROM complaints
    """
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    base_query += """
        ORDER BY
          CASE status
            WHEN 'Pending' THEN 1
            WHEN 'In Progress' THEN 2
            WHEN 'Resolved' THEN 3
            ELSE 4
          END,
          CASE priority
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
          END,
          id DESC
    """

    complaints = db.execute(
        base_query,
        params,
    ).fetchall()

    summary_rows = db.execute(
        """
        SELECT status, COUNT(*) AS total
        FROM complaints
        GROUP BY status
        """
    ).fetchall()
    summary = {"Pending": 0, "In Progress": 0, "Resolved": 0}
    for row in summary_rows:
        summary[row["status"]] = row["total"]

    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Admin Dashboard</title>
          <style>{{ style }}</style>
        </head>
        <body>
          <div class="nav">
            <a href="{{ url_for('index') }}">Home</a>
            <span class="nav-title">Admin Portal ({{ session['admin_username'] }})</span>
            <a href="{{ url_for('admin_logout') }}">Logout</a>
          </div>
          <div class="container">
            <div class="brand-header">
              <img class="brand-logo" src="{{ college_logo_url }}" alt="{{ college_name }} logo">
            </div>
            <div class="card">
              <h2>All Complaints</h2>
              <p class="small">Student identity is hidden in admin view as requested.</p>
              <p>
                <span class="chip">Pending: {{ summary['Pending'] }}</span>
                <span class="chip">In Progress: {{ summary['In Progress'] }}</span>
                <span class="chip">Resolved: {{ summary['Resolved'] }}</span>
                <span class="chip">Visible (Filtered): {{ complaints|length }}</span>
              </p>

              <form method="get">
                <label for="status_filter">Filter by Status</label>
                <select id="status_filter" name="status_filter">
                  <option value="All" {% if status_filter == 'All' %}selected{% endif %}>All</option>
                  {% for item in statuses %}
                    <option value="{{ item }}" {% if status_filter == item %}selected{% endif %}>{{ item }}</option>
                  {% endfor %}
                </select>

                <label for="category_filter">Filter by Category</label>
                <select id="category_filter" name="category_filter">
                  <option value="All" {% if category_filter == 'All' %}selected{% endif %}>All</option>
                  {% for item in categories %}
                    <option value="{{ item }}" {% if category_filter == item %}selected{% endif %}>{{ item }}</option>
                  {% endfor %}
                </select>

                <label for="priority_filter">Filter by Priority</label>
                <select id="priority_filter" name="priority_filter">
                  <option value="All" {% if priority_filter == 'All' %}selected{% endif %}>All</option>
                  {% for item in priorities %}
                    <option value="{{ item }}" {% if priority_filter == item %}selected{% endif %}>{{ item }}</option>
                  {% endfor %}
                </select>
                <button type="submit" class="btn btn-secondary">Apply Filters</button>
              </form>

              {% with messages = get_flashed_messages() %}
                {% if messages %}
                  {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                  {% endfor %}
                {% endif %}
              {% endwith %}

              {% if complaints %}
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Block</th>
                        <th>Room</th>
                        <th>Category</th>
                        <th>Priority</th>
                        <th>Description</th>
                        <th>Status</th>
                        <th>Assigned Staff</th>
                        <th>Remarks</th>
                        <th>Created</th>
                        <th>Last Updated</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                    {% for row in complaints %}
                      <tr>
                        <td>{{ row['id'] }}</td>
                        <td>{{ row['hostel_block'] }}</td>
                        <td>{{ row['room_number'] }}</td>
                        <td>{{ row['category'] }}</td>
                        <td class="{{ priority_class(row['priority']) }}">{{ row['priority'] }}</td>
                        <td>{{ row['description'] }}</td>
                        <td class="{{ status_class(row['status']) }}">{{ row['status'] }}</td>
                        <td>{{ row['staff_assigned'] or '-' }}</td>
                        <td>{{ row['remarks'] or '-' }}</td>
                        <td>{{ row['created_at'] }}</td>
                        <td>{{ row['updated_at'] or row['created_at'] }}</td>
                        <td>
                          <form method="post">
                            <input type="hidden" name="complaint_id" value="{{ row['id'] }}">
                            <input type="hidden" name="status_filter" value="{{ status_filter }}">
                            <input type="hidden" name="category_filter" value="{{ category_filter }}">
                            <input type="hidden" name="priority_filter" value="{{ priority_filter }}">
                            <label>Status</label>
                            <select name="status" required>
                              {% for item in statuses %}
                                <option value="{{ item }}" {% if item == row['status'] %}selected{% endif %}>{{ item }}</option>
                              {% endfor %}
                            </select>

                            <label>Priority</label>
                            <select name="priority" required>
                              {% for item in priorities %}
                                <option value="{{ item }}" {% if item == row['priority'] %}selected{% endif %}>{{ item }}</option>
                              {% endfor %}
                            </select>

                            <label>Assign Staff</label>
                            <input type="text" name="staff_assigned" value="{{ row['staff_assigned'] or '' }}" placeholder="e.g. Electrician Ravi">

                            <label>Remarks</label>
                            <textarea name="remarks" placeholder="Add remarks">{{ row['remarks'] or '' }}</textarea>

                            <button type="submit">Update</button>
                          </form>
                        </td>
                      </tr>
                    {% endfor %}
                    </tbody>
                  </table>
                </div>
              {% else %}
                <p class="small">No complaints available.</p>
              {% endif %}
            </div>
          </div>
        </body>
        </html>
        """,
        style=STYLE,
        complaints=complaints,
        summary=summary,
        statuses=ALLOWED_STATUSES,
        priorities=ALLOWED_PRIORITIES,
        categories=ALLOWED_CATEGORIES,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    flash("Admin logged out.")
    return redirect(url_for("admin_login"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
