# Project roadmap planning
_Exported on 3/9/2026 at 18:13:51 GMT+2 from Cursor (2.6.11)_

---

**User**

@Bet Project Characterization.pdf hi chat, read the full project characterization.
here are some keypoints:
the "bet-app" folder represents the application repo.
the "bet-infra" folder represents the infrastructure repo.
Act as a Senior DevOps Engineer with the following specifications:

*   **Core Expertise:** Kubernetes, Docker, Python, Application Deployment, CI-CD, Jenkins, terraform, azure, helm, monitoring.
*   **Tone:** Professional, precise, and direct.
*   **Instructions:**
    *   Provide production-grade, secure code and configurations.
    *   Keep explanations short, understandable, and free of conversational filler.
    *   Focus strictly on actionable technical solutions and industry best practices.

I want to plan the entire milestone with key targets on each - creating a fully detailed roadmap.
after we have our plans set-up we will start to build the project step by step according to my previos instructions and project characterization.

---

**Cursor**

Reading the full Bet Project Characterization PDF to extract requirements and produce a milestone roadmap.


Checking the current state of bet-app and bet-infra to see what's already present:


Creating a detailed milestone roadmap from the project characterization. Both repos are greenfield (only README + .git).


---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Checking the plan's to-dos and workspace state so we can implement the roadmap.


Plan shows empty todos; we're creating milestone todos and starting Phase 1 (Core Backend & Models).


Implementing Phase 1 — Core Backend & Models: creating the project structure and core files.


Using PyJWT only (no Flask-JWT-Extended) and adding views and templates.


Fixing dashboard template: Phase 1 doesn't include bet detail or create-bet routes.


Fixing the profile view query and adding run.py, Alembic, and tests.


Checking Flask-Migrate's expected layout and adding a proper migrations setup:


---

**User**

kets continue on phase 1

---

**Cursor**

Checking the Phase 1 codebase and completing any remaining items.


Completing Phase 1: adding cookie-based auth for browser flows, fixing the index redirect, fixing migrations, and adding tests.


Adding the Flask-Migrate Alembic env and creating the initial migration and tests.


Fixing the migration for PostgreSQL enum values (use value, not name):


Adding tests and pytest to requirements.


Running tests to verify:


Overriding DATABASE_URL in the test app fixture so tests use SQLite.


Setting DATABASE_URL in conftest before any app import so Config picks up SQLite.


Checking SQLite compatibility with Enum: SQLAlchemy may require native_enum=False for SQLite.


Fixing JWT import: the installed `jwt` package may be the wrong one. Using PyJWT's encode/decode explicitly:


Implementing a minimal stdlib-based JWT so the app works whether the `jwt` package or PyJWT is installed:


Using integer timestamps in the JWT payload and fixing deprecation warnings:


All tests passed. Updating the README with run instructions and marking Phase 1 complete.


Summary of what was completed for **Phase 1 – Core Backend & Models**:

**Delivered**

1. **Layout**  
   - `app/`, `tests/`, `config.py`, `requirements.txt`, `.env.example`, `run.py`.

2. **Models** ([`app/models.py`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\app\models.py))  
   - **User**: username, password_hash (bcrypt), nickname, bio, wins, losses, open_bets, aura.  
   - **Bet**: topic, description, win_prize, difficulty (enum), end_date, end_condition, status (enum), report_count, created_by_id.  
   - **Participation**: user_id, bet_id, stake, is_winner (for Phase 2).

3. **PostgreSQL / migrations**  
   - Config via `DATABASE_URL`.  
   - Alembic: [`migrations/env.py`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\migrations\env.py), [`migrations/versions/001_initial.py`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\migrations\versions\001_initial.py), [`alembic.ini`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\alembic.ini).  
   - Run: `flask db upgrade`.

4. **Auth** ([`app/auth.py`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\app\auth.py))  
   - Register / login (JSON and form).  
   - JWT (HS256) with PyJWT or stdlib fallback; integer `exp`/`iat`.  
   - Cookie `auth_token` for browser; `login_required`; redirect to login when not authenticated.

5. **Views** ([`app/views.py`](c:\Users\netan\Desktop\GitHub repositories\Sela\Projects\bet\bet-app\app\views.py))  
   - `/` → index or redirect to dashboard.  
   - `/dashboard` (open bets, login required).  
   - `/profile` (user + open bets joined, login required).  
   - `/leaderboard` (by Aura, public).  
   - `/health` (for probes).

6. **Templates**  
   - `base.html`, `index.html`, `login.html`, `register.html`, `dashboard.html`, `profile.html`, `leaderboard.html`.

7. **Security**  
   - bcrypt for passwords, validation on username/password, secrets from env (no admin role).

8. **Tests**  
   - `tests/conftest.py` (app, client, init_db; `DATABASE_URL` set to SQLite before import).  
   - `tests/test_auth.py`: register JSON, validation, login success/fail.  
   - `tests/test_views.py`: leaderboard public, dashboard requires auth, health.  
   - **All 7 tests pass.**

**How to run**

- Copy `.env.example` to `.env`, set `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`.  
- `flask db upgrade` then `python run.py`.  
- `pytest tests/ -v` to run tests.

Phase 1 is **complete**. We can move on to Phase 2 (Aura algorithm) next.

---

**User**

lets move to phase 2

