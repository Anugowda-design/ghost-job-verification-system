"""
=============================================================================
Ghost Job & Fake Recruiter Verification System
Innovation: Hiring Intent Lock
Stack: Python Flask, SQLite, Semantic HTML5 + Modern CSS3 (No JS, No Blockchain)
=============================================================================
"""

import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session, render_template, flash, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hiring-intent-lock-secret-key-2026")
app.config["TEMPLATES_AUTO_RELOAD"] = True

DB = "hiring_lock.db"


# =============================================================================
# DATABASE UTILITIES & INITIALIZATION
# =============================================================================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    # 1. Recruiters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            verified INTEGER DEFAULT 1
        )
    """)

    # 2. Jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            salary TEXT NOT NULL,
            vacancies INTEGER NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY (recruiter_id) REFERENCES recruiters(id)
        )
    """)

    # 3. Hiring Intent Locks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            recruiter_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expiry_at TEXT NOT NULL,
            hash TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (recruiter_id) REFERENCES recruiters(id)
        )
    """)

    # 4. Applications table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            applicant_name TEXT NOT NULL,
            applicant_email TEXT NOT NULL,
            phone TEXT NOT NULL,
            resume TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    conn.commit()
    conn.close()


def generate_hash(recruiter_id, job_id, created, expiry):
    """
    Computes a deterministic SHA-256 cryptographic proof for the hiring intent lock.
    Formula: SHA256(recruiter_id|job_id|created|expiry)
    """
    payload = f"{recruiter_id}|{job_id}|{created}|{expiry}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Initialize SQLite tables on startup
init_db()


# =============================================================================
# MODULE 9: AUTOMATIC JOB EXPIRY ENGINE
# =============================================================================

def check_expired_locks():
    """
    Scans all ACTIVE locks against the current timestamp.
    If now >= expiry_at, automatically flips status to EXPIRED and deactivates job.
    This guarantees ghost job prevention.
    """
    conn = get_db()
    locks = conn.execute("SELECT * FROM locks WHERE status='ACTIVE'").fetchall()
    now = datetime.now()

    for lock in locks:
        expiry = datetime.fromisoformat(lock["expiry_at"])
        if now >= expiry:
            conn.execute("UPDATE locks SET status='EXPIRED' WHERE id=?", (lock["id"],))
            conn.execute("UPDATE jobs SET status='INACTIVE' WHERE id=?", (lock["job_id"],))

    conn.commit()
    conn.close()


# =============================================================================
# MODULE 1: HOME PAGE
# =============================================================================

@app.route("/")
def home():
    check_expired_locks()
    conn = get_db()

    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    active_locks = conn.execute("SELECT COUNT(*) FROM locks WHERE status='ACTIVE'").fetchone()[0]
    expired_locks = conn.execute("SELECT COUNT(*) FROM locks WHERE status='EXPIRED'").fetchone()[0]
    total_recruiters = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]

    conn.close()

    stats = {
        "total_jobs": total_jobs,
        "active_locks": active_locks,
        "expired_locks": expired_locks,
        "total_recruiters": total_recruiters
    }

    return render_template("index.html", stats=stats, active_page="home")


# =============================================================================
# MODULE 2: RECRUITER REGISTRATION
# =============================================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not company or not email or not password:
            flash("All fields are required for recruiter verification.", "danger")
            return render_template("register.html", active_page="register")

        conn = get_db()
        try:
            cursor = conn.execute("""
                INSERT INTO recruiters (name, company, email, password, verified)
                VALUES (?, ?, ?, ?, 1)
            """, (name, company, email, password))
            conn.commit()
            session["recruiter_id"] = cursor.lastrowid
            conn.close()

            flash(f"Welcome, {name}! Your recruiter account at {company} has been verified.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            conn.close()
            flash("That corporate email is already registered. Please log in.", "warning")
            return redirect(url_for("login"))

    return render_template("register.html", active_page="register")


# =============================================================================
# MODULE 3: RECRUITER LOGIN
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        recruiter = conn.execute("""
            SELECT * FROM recruiters WHERE email=? AND password=?
        """, (email, password)).fetchone()
        conn.close()

        if recruiter:
            session["recruiter_id"] = recruiter["id"]
            flash(f"Signed in successfully as {recruiter['name']} ({recruiter['company']}).", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html", active_page="login")


# =============================================================================
# MODULE 4: RECRUITER DASHBOARD
# =============================================================================

@app.route("/dashboard")
def dashboard():
    if "recruiter_id" not in session:
        flash("Please log in to access the recruiter dashboard.", "warning")
        return redirect(url_for("login"))

    check_expired_locks()
    recruiter_id = session["recruiter_id"]

    conn = get_db()
    recruiter = conn.execute("SELECT * FROM recruiters WHERE id=?", (recruiter_id,)).fetchone()

    jobs = conn.execute("""
        SELECT jobs.*, locks.expiry_at, locks.status AS lock_status, locks.hash
        FROM jobs
        LEFT JOIN locks ON jobs.id = locks.job_id
        WHERE jobs.recruiter_id=?
        ORDER BY jobs.id DESC
    """, (recruiter_id,)).fetchall()

    total_applications_count = conn.execute("""
        SELECT COUNT(*) FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE jobs.recruiter_id=?
    """, (recruiter_id,)).fetchone()[0]

    conn.close()

    if not recruiter:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        recruiter=recruiter,
        jobs=jobs,
        total_applications_count=total_applications_count,
        active_page="dashboard"
    )


# =============================================================================
# MODULE 5: CREATE JOB POSTING
# =============================================================================

@app.route("/create-job", methods=["GET", "POST"])
def create_job():
    if "recruiter_id" not in session:
        flash("You must be logged in as a verified recruiter to post jobs.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        salary = request.form.get("salary", "").strip()
        vacancies = int(request.form.get("vacancies", 1))
        duration = int(request.form.get("duration", 30))

        recruiter_id = session["recruiter_id"]
        created = datetime.now()
        expiry = created + timedelta(days=duration)

        created_text = created.isoformat()
        expiry_text = expiry.isoformat()

        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO jobs (recruiter_id, title, description, location, salary, vacancies, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (recruiter_id, title, description, location, salary, vacancies))

        job_id = cursor.lastrowid

        # Module 6: Generate SHA-256 Intent Lock
        lock_hash = generate_hash(recruiter_id, job_id, created_text, expiry_text)

        conn.execute("""
            INSERT INTO locks (job_id, recruiter_id, created_at, expiry_at, hash, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (job_id, recruiter_id, created_text, expiry_text, lock_hash))

        conn.commit()
        conn.close()

        flash("Job successfully posted and backed by an active Hiring Intent Lock!", "success")
        return redirect(f"/lock/{job_id}")

    return render_template("create_job.html", active_page="create_job")


# =============================================================================
# MODULE 6: HIRING INTENT LOCK ACTIVATION CERTIFICATE
# =============================================================================

@app.route("/lock/<int:job_id>")
def lock_details(job_id):
    check_expired_locks()
    conn = get_db()

    lock = conn.execute("""
        SELECT locks.*, jobs.title, recruiters.company, recruiters.name as recruiter_name
        FROM locks
        JOIN jobs ON locks.job_id = jobs.id
        JOIN recruiters ON locks.recruiter_id = recruiters.id
        WHERE jobs.id=?
    """, (job_id,)).fetchone()

    conn.close()

    if not lock:
        flash(f"Lock certificate for Job #{job_id} not found.", "danger")
        return redirect(url_for("jobs"))

    return render_template("lock_details.html", lock=lock, active_page="verify")


# =============================================================================
# MODULE 7: JOB SEEKER – VIEW JOBS
# =============================================================================

@app.route("/jobs")
def jobs():
    check_expired_locks()
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    status_filter = request.args.get("status", "ACTIVE")

    conn = get_db()
    query = """
        SELECT jobs.*, recruiters.company, locks.expiry_at, locks.status AS lock_status, locks.hash
        FROM jobs
        JOIN recruiters ON jobs.recruiter_id = recruiters.id
        LEFT JOIN locks ON jobs.id = locks.job_id
        WHERE 1=1
    """
    params = []

    if status_filter == "ACTIVE":
        query += " AND jobs.status='ACTIVE' AND locks.status='ACTIVE'"
    elif status_filter == "EXPIRED":
        query += " AND locks.status='EXPIRED'"

    if q:
        query += " AND (jobs.title LIKE ? OR jobs.description LIKE ? OR recruiters.company LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term])

    if location:
        query += " AND jobs.location LIKE ?"
        params.append(f"%{location}%")

    query += " ORDER BY jobs.id DESC"
    jobs_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("jobs.html", jobs=jobs_list, active_page="jobs")


# =============================================================================
# MODULE 8: JOB VERIFICATION ENGINE
# =============================================================================

@app.route("/verify")
def verify():
    check_expired_locks()
    query = request.args.get("query", "").strip()
    result = None

    if query:
        conn = get_db()
        job = None

        # Check if query is numeric (Job ID)
        if query.isdigit():
            job = conn.execute("""
                SELECT jobs.*, recruiters.company, recruiters.name as recruiter_name,
                       locks.created_at, locks.expiry_at, locks.hash, locks.status as lock_status
                FROM jobs
                JOIN recruiters ON jobs.recruiter_id = recruiters.id
                JOIN locks ON jobs.id = locks.job_id
                WHERE jobs.id=?
            """, (int(query),)).fetchone()

        # If not found, check by SHA-256 hash
        if not job:
            job = conn.execute("""
                SELECT jobs.*, recruiters.company, recruiters.name as recruiter_name,
                       locks.created_at, locks.expiry_at, locks.hash, locks.status as lock_status
                FROM jobs
                JOIN recruiters ON jobs.recruiter_id = recruiters.id
                JOIN locks ON jobs.id = locks.job_id
                WHERE locks.hash=?
            """, (query,)).fetchone()

        conn.close()

        if job:
            # Recompute hash to verify cryptographic integrity
            expected_hash = generate_hash(
                job["recruiter_id"],
                job["id"],
                job["created_at"],
                job["expiry_at"]
            )
            hash_valid = (expected_hash == job["hash"])
            is_active = (job["lock_status"] == "ACTIVE")

            result = {
                "found": True,
                "job": job,
                "hash_valid": hash_valid,
                "is_active": is_active
            }
        else:
            result = {"found": False}

    return render_template("verify.html", query=query, result=result, active_page="verify")


# =============================================================================
# JOB APPLICATION (CANDIDATE SUBMISSION)
# =============================================================================

@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):
    check_expired_locks()
    conn = get_db()

    job = conn.execute("""
        SELECT jobs.*, recruiters.company, locks.status AS lock_status, locks.expiry_at
        FROM jobs
        JOIN recruiters ON jobs.recruiter_id = recruiters.id
        LEFT JOIN locks ON jobs.id = locks.job_id
        WHERE jobs.id=?
    """, (job_id,)).fetchone()

    if not job:
        conn.close()
        flash("The requested job does not exist.", "danger")
        return redirect(url_for("jobs"))

    if job["lock_status"] != "ACTIVE":
        conn.close()
        flash("Applications for this position are closed because the Hiring Intent Lock has expired.", "danger")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        resume = request.form.get("resume", "").strip()

        if not name or not email or not phone or not resume:
            flash("Please fill out all application fields.", "warning")
            return render_template("apply.html", job=job, active_page="jobs")

        conn.execute("""
            INSERT INTO applications (job_id, applicant_name, applicant_email, phone, resume, applied_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, name, email, phone, resume, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        flash(f"🎉 Application submitted successfully for {job['title']} at {job['company']}!", "success")
        return redirect(url_for("jobs"))

    conn.close()
    return render_template("apply.html", job=job, active_page="jobs")


# =============================================================================
# RECRUITER APPLICATIONS MANAGER
# =============================================================================

@app.route("/applications")
def applications():
    if "recruiter_id" not in session:
        flash("Please log in to review applicant submissions.", "warning")
        return redirect(url_for("login"))

    recruiter_id = session["recruiter_id"]
    conn = get_db()

    applications_list = conn.execute("""
        SELECT applications.*, jobs.title
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE jobs.recruiter_id=?
        ORDER BY applications.id DESC
    """, (recruiter_id,)).fetchall()

    conn.close()
    return render_template("applications.html", applications=applications_list, active_page="dashboard")


# =============================================================================
# MODULE 10: LOGOUT
# =============================================================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("home"))


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
