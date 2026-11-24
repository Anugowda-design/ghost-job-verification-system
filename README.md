# Ghost Job & Fake Recruiter Verification System
> **Innovation:** Deterministic Hiring Intent Lock Network  
> **Tech Stack:** Python (Flask), SQLite, Semantic HTML5 + Modern CSS3 (No JavaScript, No Blockchain)

---

## 1. Project Overview

The **Ghost Job & Fake Recruiter Verification System** is an anti-fraud web platform designed to combat phantom job listings ("ghost jobs") and unverified recruiters. It introduces the **Hiring Intent Lock**—a tamper-evident cryptographic mechanism powered by deterministic SHA-256 hashing and automated expiration.

### Core Problems Solved:
1. **Ghost Jobs:** Postings kept perpetually open without hiring budget or active hiring intent to harvest resumes or artificially inflate company growth metrics.
2. **Fake Recruiters & Phishing:** Bad actors posing as corporate talent acquisition to collect sensitive candidate data.
3. **Application Black Holes:** Job seekers spending hours applying to positions that were closed weeks or months prior.

---

## 2. Technical Stack (Final Setup Alignment)

* **Domain:** Web Application Development
* **Frontend:** Semantic HTML5 & Modern CSS3 (**Strictly Zero JavaScript dependency**)
* **Backend:** Python 3.10+ / Flask Framework
* **Database:** SQLite3 (`hiring_lock.db`)
* **Cryptography:** Python Standard `hashlib` (SHA-256 deterministic commitment, **No Blockchain overhead**)
* **Server & Deployment:** Gunicorn WSGI Server (Ready for Render / Linux PaaS deployment)

---

## 3. The 10 Website Modules

1. **Home Page (`/`)**: Hero section, real-time metrics (Total Jobs, Active Locks, Expired Postings, Verified Employers), 4-step workflow, and instant verification search bar.
2. **Recruiter Registration (`/register`)**: Corporate identity vetting, verified recruiter badge generation, duplicate account protection.
3. **Recruiter Login (`/login`)**: Session authentication and credential protection.
4. **Recruiter Dashboard (`/dashboard`)**: Managed jobs overview, active vs. expired status tags, direct links to lock certificates, and application review.
5. **Create Job Posting (`/create-job`)**: Input title, description, location, comp range, vacancies, and select hiring duration (15, 30, 45, or 60 days).
6. **Hiring Intent Lock Activation (`/lock/<id>`)**: Calculates deterministic SHA-256 cryptographic proof and issues an audit certificate.
7. **Job Seeker – View Jobs (`/jobs`)**: Filter by keyword and location using pure HTML forms, showing anti-ghost active lock indicators and expiration dates.
8. **Job Verification Engine (`/verify`)**: Dedicated audit tool to look up any Job ID or 64-character SHA-256 hash, recalculating and verifying mathematical integrity on the fly.
9. **Automatic Job Expiry (`check_expired_locks()`)**: Background check automatically transitions expired postings to `INACTIVE` and blocks further applications, eliminating ghost jobs.
10. **Logout (`/logout`)**: Safely clears authenticated recruiter sessions.

---

## 4. How the Hiring Intent Lock Works

### Mathematical Formula:
$$\text{Lock Hash} = \text{SHA-256}(\text{recruiter\_id} \parallel \text{job\_id} \parallel \text{created\_at} \parallel \text{expiry\_at})$$

### Lifecycle Workflow:
1. **Employer Vetting:** Recruiter registers corporate identity.
2. **Intent Commitment:** Recruiter commits to an active hiring window (15–60 days) and open headcount.
3. **Cryptographic Sealing:** The system computes the immutable SHA-256 lock hash stored in SQLite.
4. **Verification & Audit:** Candidates and auditors verify lock validity via `/verify` on demand.
5. **Automated Deactivation:** If `current_time >= expiry_at`, the system transitions the lock to `EXPIRED` and closes applications automatically.

---

## 5. Local Setup & Execution

### Prerequisites:
* Python 3.10+
* pip

### Installation:
```bash
git clone https://github.com/your-repo/ghost-job-verification-system.git
cd ghost-job-verification-system
pip install -r requirements.txt
```

### Running Locally:
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

### Production Deployment (e.g., Render):
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `gunicorn app:app`
