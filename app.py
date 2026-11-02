from flask import Flask, request, redirect, session, render_template_string
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "hiring-intent-lock-secret"

DB = "hiring_lock.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # Recruiters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            company TEXT,
            email TEXT UNIQUE,
            password TEXT,
            verified INTEGER DEFAULT 0
        )
    """)

    # Jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER,
            title TEXT,
            description TEXT,
            location TEXT,
            salary TEXT,
            vacancies INTEGER,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)

    # Hiring Intent Lock table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            recruiter_id INTEGER,
            created_at TEXT,
            expiry_at TEXT,
            hash TEXT,
            status TEXT
        )
    """)

    # Applications table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            applicant_name TEXT,
            applicant_email TEXT,
            phone TEXT,
            resume TEXT,
            applied_at TEXT
        )
    """)

    conn.commit()
    conn.close()
# Create database tables when the app starts
init_db()


# =========================================================
# SHA-256 HASH
# =========================================================

def generate_hash(recruiter_id, job_id, created, expiry):

    data = f"{recruiter_id}|{job_id}|{created}|{expiry}"

    return hashlib.sha256(data.encode()).hexdigest()


# =========================================================
# CHECK EXPIRED LOCKS
# =========================================================

def check_expired_locks():

    conn = get_db()

    locks = conn.execute(
        "SELECT * FROM locks WHERE status='ACTIVE'"
    ).fetchall()

    now = datetime.now()

    for lock in locks:

        expiry = datetime.fromisoformat(
            lock["expiry_at"]
        )

        if now >= expiry:

            conn.execute(
                """
                UPDATE locks
                SET status='EXPIRED'
                WHERE id=?
                """,
                (lock["id"],)
            )

            conn.execute(
                """
                UPDATE jobs
                SET status='INACTIVE'
                WHERE id=?
                """,
                (lock["job_id"],)
            )

    conn.commit()
    conn.close()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    check_expired_locks()

    return render_template_string("""

<!DOCTYPE html>

<html>

<head>

<title>Hiring Intent Lock</title>

<style>

body {
    font-family: Arial;
    margin: 0;
    background: #f4f6f8;
}

header {
    background: #17202a;
    color: white;
    padding: 25px;
    text-align: center;
}

.container {
    width: 85%;
    margin: 40px auto;
    text-align: center;
}

.card {
    background: white;
    padding: 30px;
    margin: 20px;
    border-radius: 12px;
    box-shadow: 0 3px 10px #ccc;
}

a, button {
    background: #2874a6;
    color: white;
    padding: 12px 20px;
    border: none;
    border-radius: 6px;
    text-decoration: none;
    margin: 5px;
    cursor: pointer;
}

.green {
    color: green;
    font-weight: bold;
}

</style>

</head>

<body>

<header>

<h1>🔐 Hiring Intent Lock</h1>

<p>
Ghost Job & Fake Recruiter Verification Network
</p>

</header>

<div class="container">

<div class="card">

<h2>For Recruiters</h2>

<p>
Verify yourself and create genuine job postings.
</p>

<a href="/register">
Register
</a>

<a href="/login">
Login
</a>

</div>


<div class="card">

<h2>For Job Seekers</h2>

<p>
Check whether a job has an active Hiring Intent Lock.
</p>

<a href="/jobs">
View Jobs
</a>

</div>


<div class="card">

<h2>How It Works</h2>

<p>

Verified Recruiter →
Job Post →
Hiring Intent Lock →
SHA-256 →
Blockchain Record →
Automatic Expiry

</p>

<p class="green">

🟢 Active Lock = Active Hiring

</p>

</div>

</div>

</body>

</html>

""")


# =========================================================
# RECRUITER REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        company = request.form["company"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO recruiters
                (name, company, email, password, verified)
                VALUES (?, ?, ?, ?, 1)
            """,
            (
                name,
                company,
                email,
                password
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "Email already registered."

        conn.close()

        return redirect("/login")


    return render_template_string("""

<html>

<head>

<title>Recruiter Registration</title>

<style>

body {
    font-family: Arial;
    background: #eef2f3;
}

.box {
    width: 400px;
    margin: 60px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 3px 10px #bbb;
}

input {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 12px;
    background: #2874a6;
    color: white;
    border: none;
    cursor: pointer;
}

</style>

</head>

<body>

<div class="box">

<h2>Recruiter Registration</h2>

<form method="POST">

<input
name="name"
placeholder="Recruiter Name"
required
>

<input
name="company"
placeholder="Company Name"
required
>

<input
name="email"
type="email"
placeholder="Company Email"
required
>

<input
name="password"
type="password"
placeholder="Password"
required
>

<button>
Register & Verify
</button>

</form>

</div>

</body>

</html>

""")


# =========================================================
# RECRUITER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        recruiter = conn.execute("""
            SELECT *
            FROM recruiters
            WHERE email=? AND password=?
        """,
        (
            email,
            password
        )).fetchone()

        conn.close()

        if recruiter:

            session["recruiter_id"] = recruiter["id"]

            return redirect("/dashboard")

        return "Invalid email or password."


    return render_template_string("""

<html>

<head>

<title>Recruiter Login</title>

<style>

body {
    font-family: Arial;
    background: #eef2f3;
}

.box {
    width: 400px;
    margin: 80px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 3px 10px #bbb;
}

input {
    width: 100%;
    padding: 12px;
    margin: 10px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 12px;
    background: #2874a6;
    color: white;
    border: none;
    cursor: pointer;
}

</style>

</head>

<body>

<div class="box">

<h2>Recruiter Login</h2>

<form method="POST">

<input
name="email"
type="email"
placeholder="Email"
required
>

<input
name="password"
type="password"
placeholder="Password"
required
>

<button>
Login
</button>

</form>

</div>

</body>

</html>

""")


# =========================================================
# RECRUITER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "recruiter_id" not in session:

        return redirect("/login")

    check_expired_locks()

    recruiter_id = session["recruiter_id"]

    conn = get_db()

    recruiter = conn.execute(
        """
        SELECT *
        FROM recruiters
        WHERE id=?
        """,
        (recruiter_id,)
    ).fetchone()

    jobs = conn.execute("""
        SELECT
            jobs.*,
            locks.expiry_at,
            locks.status AS lock_status
        FROM jobs
        LEFT JOIN locks
        ON jobs.id = locks.job_id
        WHERE jobs.recruiter_id=?
    """,
    (recruiter_id,)).fetchall()

    conn.close()


    return render_template_string("""

<html>

<head>

<title>Recruiter Dashboard</title>

<style>

body {
    font-family: Arial;
    background: #f4f6f8;
    margin: 0;
}

header {
    background: #17202a;
    color: white;
    padding: 20px;
}

.container {
    width: 90%;
    margin: 30px auto;
}

.card {
    background: white;
    padding: 25px;
    margin: 20px 0;
    border-radius: 12px;
    box-shadow: 0 3px 10px #ccc;
}

.active {
    color: green;
    font-weight: bold;
}

.expired {
    color: red;
    font-weight: bold;
}

a {
    background: #2874a6;
    color: white;
    padding: 10px;
    text-decoration: none;
    border-radius: 5px;
    margin-right: 5px;
}

</style>

</head>

<body>

<header>

<h1>
Recruiter Dashboard
</h1>

<p>
Welcome {{ recruiter["name"] }}
</p>

<p>
Recruiter Status:
<b>✅ VERIFIED</b>
</p>

</header>


<div class="container">

<a href="/create-job">
+ Create New Job
</a>

<a href="/applications">
View Applications
</a>

<a href="/logout">
Logout
</a>


<h2>
My Jobs
</h2>


{% for job in jobs %}

<div class="card">

<h2>
{{ job["title"] }}
</h2>

<p>
{{ job["description"] }}
</p>

<p>
Location: {{ job["location"] }}
</p>

<p>
Salary: {{ job["salary"] }}
</p>

<p>
Vacancies: {{ job["vacancies"] }}
</p>


{% if job["lock_status"] == "ACTIVE" %}

<p class="active">

🔒 Hiring Intent Lock: ACTIVE

</p>

<p>
Expires:
{{ job["expiry_at"] }}
</p>

{% else %}

<p class="expired">

🔴 Hiring Intent Lock: EXPIRED

</p>

{% endif %}

</div>

{% else %}

<p>
No jobs created yet.
</p>

{% endfor %}

</div>

</body>

</html>

""",
recruiter=recruiter,
jobs=jobs)


# =========================================================
# CREATE JOB + HIRING INTENT LOCK
# =========================================================

@app.route("/create-job", methods=["GET", "POST"])
def create_job():

    if "recruiter_id" not in session:

        return redirect("/login")


    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        salary = request.form["salary"]
        vacancies = request.form["vacancies"]
        duration = int(request.form["duration"])

        recruiter_id = session["recruiter_id"]

        created = datetime.now()

        expiry = created + timedelta(
            days=duration
        )

        created_text = created.isoformat()
        expiry_text = expiry.isoformat()

        conn = get_db()


        cursor = conn.execute("""
            INSERT INTO jobs
            (
                recruiter_id,
                title,
                description,
                location,
                salary,
                vacancies,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
        """,
        (
            recruiter_id,
            title,
            description,
            location,
            salary,
            vacancies
        ))


        job_id = cursor.lastrowid


        # Generate SHA-256 hash

        lock_hash = generate_hash(
            recruiter_id,
            job_id,
            created_text,
            expiry_text
        )


        # Create Hiring Intent Lock

        conn.execute("""
            INSERT INTO locks
            (
                job_id,
                recruiter_id,
                created_at,
                expiry_at,
                hash,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """,
        (
            job_id,
            recruiter_id,
            created_text,
            expiry_text,
            lock_hash
        ))


        conn.commit()
        conn.close()


        return redirect(
            "/lock/" + str(job_id)
        )


    return render_template_string("""

<html>

<head>

<title>Create Job</title>

<style>

body {
    font-family: Arial;
    background: #eef2f3;
}

.box {
    width: 600px;
    margin: 40px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 3px 10px #bbb;
}

input, textarea {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}

button {
    padding: 13px;
    width: 100%;
    background: #2874a6;
    color: white;
    border: none;
    cursor: pointer;
}

</style>

</head>

<body>

<div class="box">

<h2>
Create Job & Hiring Intent Lock
</h2>

<form method="POST">

<input
name="title"
placeholder="Job Title"
required
>

<textarea
name="description"
placeholder="Job Description"
required>
</textarea>

<input
name="location"
placeholder="Location"
required
>

<input
name="salary"
placeholder="Salary"
required
>

<input
name="vacancies"
type="number"
min="1"
placeholder="Number of Vacancies"
required
>

<input
name="duration"
type="number"
min="1"
value="30"
placeholder="Lock Duration in Days"
required
>

<button>

🔒 CREATE HIRING INTENT LOCK

</button>

</form>

</div>

</body>

</html>

""")


# =========================================================
# LOCK DETAILS
# =========================================================

@app.route("/lock/<int:job_id>")
def lock_details(job_id):

    conn = get_db()

    lock = conn.execute("""
        SELECT
            locks.*,
            jobs.title
        FROM locks
        JOIN jobs
        ON locks.job_id = jobs.id
        WHERE jobs.id=?
    """,
    (job_id,)).fetchone()

    conn.close()


    if not lock:

        return "Lock not found."


    return render_template_string("""

<html>

<head>

<title>Hiring Intent Lock</title>

<style>

body {
    font-family: Arial;
    background: #f4f6f8;
}

.lock {
    width: 650px;
    margin: 60px auto;
    background: white;
    padding: 35px;
    border-radius: 15px;
    box-shadow: 0 3px 15px #bbb;
}

.active {
    color: green;
    font-size: 22px;
    font-weight: bold;
}

.hash {
    word-break: break-all;
    background: #eee;
    padding: 15px;
}

a {
    background: #2874a6;
    color: white;
    padding: 10px 15px;
    text-decoration: none;
    border-radius: 5px;
}

</style>

</head>

<body>

<div class="lock">

<h1>
🔐 Hiring Intent Lock
</h1>

<h2>
{{ lock["title"] }}
</h2>

<p>
Recruiter ID:
{{ lock["recruiter_id"] }}
</p>

<p>
Job ID:
{{ lock["job_id"] }}
</p>

<p>
Created:
{{ lock["created_at"] }}
</p>

<p>
Expiry:
{{ lock["expiry_at"] }}
</p>

<p class="active">

🟢 {{ lock["status"] }}

</p>

<h3>
SHA-256 Blockchain Hash
</h3>

<p class="hash">
{{ lock["hash"] }}
</p>

<p>
⛓️ Blockchain Record: VERIFIED
</p>

<a href="/dashboard">
Back to Dashboard
</a>

</div>

</body>

</html>

""", lock=lock)


# =========================================================
# JOB SEEKER - VIEW JOBS
# =========================================================

@app.route("/jobs")
def jobs():

    check_expired_locks()

    conn = get_db()

    jobs = conn.execute("""
        SELECT
            jobs.*,
            recruiters.company,
            locks.expiry_at,
            locks.status AS lock_status
        FROM jobs

        JOIN recruiters
        ON jobs.recruiter_id = recruiters.id

        LEFT JOIN locks
        ON jobs.id = locks.job_id

        WHERE jobs.status='ACTIVE'
    """).fetchall()

    conn.close()


    return render_template_string("""

<html>

<head>

<title>Available Jobs</title>

<style>

body {
    font-family: Arial;
    background: #f4f6f8;
}

.container {
    width: 85%;
    margin: 40px auto;
}

.job {
    background: white;
    padding: 25px;
    margin: 20px 0;
    border-radius: 12px;
    box-shadow: 0 3px 10px #ccc;
}

.verified {
    color: green;
    font-weight: bold;
}

.lock {
    color: green;
    font-weight: bold;
}

.apply {
    display: inline-block;
    background: #2874a6;
    color: white;
    padding: 12px 20px;
    text-decoration: none;
    border-radius: 6px;
}

</style>

</head>

<body>

<div class="container">

<h1>
🔎 Available Jobs
</h1>


{% for job in jobs %}

<div class="job">

<h2>
{{ job["title"] }}
</h2>

<h3>
{{ job["company"] }}
</h3>

<p>
{{ job["description"] }}
</p>

<p>
📍 {{ job["location"] }}
</p>

<p>
💰 {{ job["salary"] }}
</p>

<p>
👥 Vacancies:
{{ job["vacancies"] }}
</p>

<p class="verified">
Recruiter: ✅ VERIFIED
</p>

{% if job["lock_status"] == "ACTIVE" %}

<p class="lock">
Hiring Intent Lock: 🟢 ACTIVE
</p>

<p>
Lock expires:
{{ job["expiry_at"] }}
</p>

<a
href="/apply/{{ job['id'] }}"
class="apply"
>
APPLY NOW
</a>

{% else %}

<p>
🔴 Hiring Intent Lock EXPIRED
</p>

{% endif %}

</div>


{% else %}

<h2>
No active jobs available.
</h2>

{% endfor %}

</div>

</body>

</html>

""", jobs=jobs)


# =========================================================
# JOB APPLICATION
# =========================================================

@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):

    conn = get_db()

    job = conn.execute("""
        SELECT
            jobs.*,
            recruiters.company,
            locks.status AS lock_status
        FROM jobs

        JOIN recruiters
        ON jobs.recruiter_id = recruiters.id

        LEFT JOIN locks
        ON jobs.id = locks.job_id

        WHERE jobs.id=?
        AND jobs.status='ACTIVE'
    """,
    (job_id,)).fetchone()

    conn.close()


    if not job:

        return "Job not found or no longer active."


    if job["lock_status"] != "ACTIVE":

        return "Applications are closed because the Hiring Intent Lock has expired."


    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        resume = request.form["resume"]


        conn = get_db()

        conn.execute("""
            INSERT INTO applications
            (
                job_id,
                applicant_name,
                applicant_email,
                phone,
                resume,
                applied_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            name,
            email,
            phone,
            resume,
            datetime.now().isoformat()
        ))


        conn.commit()
        conn.close()


        return render_template_string("""

<html>

<head>

<title>Application Submitted</title>

<style>

body {
    font-family: Arial;
    background: #f4f6f8;
    text-align: center;
    padding: 80px;
}

.box {
    background: white;
    padding: 40px;
    border-radius: 15px;
    max-width: 600px;
    margin: auto;
    box-shadow: 0 3px 15px #ccc;
}

.success {
    color: green;
    font-size: 24px;
    font-weight: bold;
}

a {
    display: inline-block;
    margin-top: 20px;
    background: #2874a6;
    color: white;
    padding: 12px 20px;
    text-decoration: none;
    border-radius: 6px;
}

</style>

</head>

<body>

<div class="box">

<h1>
🎉 Application Submitted
</h1>

<p class="success">
✅ Your application has been submitted successfully.
</p>

<p>
Job:
{{ job["title"] }}
</p>

<p>
Company:
{{ job["company"] }}
</p>

<p>
🔒 Hiring Intent Lock:
ACTIVE
</p>

<a href="/jobs">
Back to Jobs
</a>

</div>

</body>

</html>

""", job=job)


    return render_template_string("""

<html>

<head>

<title>Apply for Job</title>

<style>

body {
    font-family: Arial;
    background: #eef2f3;
}

.box {
    width: 500px;
    margin: 50px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 3px 10px #bbb;
}

input {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 13px;
    background: #2874a6;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.info {
    background: #e8f8f5;
    padding: 15px;
    border-radius: 8px;
}

</style>

</head>

<body>

<div class="box">

<h2>
Apply for {{ job["title"] }}
</h2>

<p>
Company:
{{ job["company"] }}
</p>

<p class="info">

🔒 Hiring Intent Lock:
<b>ACTIVE</b>

</p>


<form method="POST">

<input
name="name"
placeholder="Your Name"
required
>

<input
name="email"
type="email"
placeholder="Your Email"
required
>

<input
name="phone"
placeholder="Phone Number"
required
>

<input
name="resume"
placeholder="Resume Link / File Name"
required
>

<button>
Submit Application
</button>

</form>

</div>

</body>

</html>

""", job=job)


# =========================================================
# RECRUITER - VIEW APPLICATIONS
# =========================================================

@app.route("/applications")
def applications():

    if "recruiter_id" not in session:

        return redirect("/login")


    recruiter_id = session["recruiter_id"]

    conn = get_db()

    applications = conn.execute("""
        SELECT
            applications.*,
            jobs.title
        FROM applications

        JOIN jobs
        ON applications.job_id = jobs.id

        WHERE jobs.recruiter_id=?

        ORDER BY applications.id DESC
    """,
    (recruiter_id,)).fetchall()

    conn.close()


    return render_template_string("""

<html>

<head>

<title>Applications</title>

<style>

body {
    font-family: Arial;
    background: #f4f6f8;
}

.container {
    width: 90%;
    margin: 40px auto;
}

.card {
    background: white;
    padding: 25px;
    margin: 20px 0;
    border-radius: 12px;
    box-shadow: 0 3px 10px #ccc;
}

a {
    background: #2874a6;
    color: white;
    padding: 10px 15px;
    text-decoration: none;
    border-radius: 5px;
}

</style>

</head>

<body>

<div class="container">

<h1>
📋 Job Applications
</h1>

<a href="/dashboard">
Back to Dashboard
</a>


{% for application in applications %}

<div class="card">

<h2>
{{ application["title"] }}
</h2>

<p>
<b>Applicant:</b>
{{ application["applicant_name"] }}
</p>

<p>
<b>Email:</b>
{{ application["applicant_email"] }}
</p>

<p>
<b>Phone:</b>
{{ application["phone"] }}
</p>

<p>
<b>Resume:</b>
{{ application["resume"] }}
</p>

<p>
<b>Applied:</b>
{{ application["applied_at"] }}
</p>

</div>


{% else %}

<p>
No applications received yet.
</p>

{% endfor %}

</div>

</body>

</html>

""", applications=applications)


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
