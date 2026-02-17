from flask import Flask, jsonify, request
import sqlite3
import csv
import json
import sys
from pathlib import Path

# ================= APP BASE DIR =================
def app_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = app_base_dir()

# ================= PATHS =================
DATA_DIR = BASE_DIR / "data"
QRS_DIR = BASE_DIR / "qrs"
EVENTS_FILE = DATA_DIR / "events.json"

DATA_DIR.mkdir(exist_ok=True)
QRS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# ================= EVENT HELPERS =================
def load_events():
    if not EVENTS_FILE.exists():
        events = {
            "active": None,
            "events": {}
        }
        save_events(events)
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

def get_active_event():
    events = load_events()
    active = events.get("active")
    if not active or active not in events["events"]:
        raise RuntimeError("No active event selected")
    return active

def get_active_db():
    return DATA_DIR / f"{get_active_event()}.db"

def get_active_csv():
    return BASE_DIR / f"{get_active_event()}_invites.csv"

# ================= DB INIT =================
def init_db():
    db_path = get_active_db()
    csv_path = get_active_csv()

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            token TEXT PRIMARY KEY,
            used INTEGER DEFAULT 0
        )
    """)

    # Import CSV tokens (SAFE: can be run multiple times)
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if not row:
                    continue
                token = row[0].strip()
                if token:
                    cur.execute(
                        "INSERT OR IGNORE INTO invites(token) VALUES (?)",
                        (token,)
                    )

    con.commit()
    con.close()

# ================= INIT ON START =================
try:
    init_db()
except RuntimeError:
    # No active event yet → admin must create one
    pass

# ================= ROUTES =================
@app.route("/scan/<token>", methods=["POST"])
def scan(token):
    con = sqlite3.connect(get_active_db())
    cur = con.cursor()

    cur.execute("SELECT used FROM invites WHERE token=?", (token,))
    row = cur.fetchone()

    if not row:
        con.close()
        return jsonify(success=False, msg="Invalid token")

    if row[0] == 1:
        con.close()
        return jsonify(success=False, msg="Already entered")

    cur.execute("UPDATE invites SET used=1 WHERE token=?", (token,))
    con.commit()

    cur.execute("SELECT COUNT(*) FROM invites WHERE used=0")
    remaining = cur.fetchone()[0]

    con.close()
    return jsonify(success=True, remaining=remaining)

@app.route("/stats")
def stats():
    con = sqlite3.connect(get_active_db())
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM invites")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM invites WHERE used=1")
    used = cur.fetchone()[0]

    con.close()
    return jsonify(
        total=total,
        used=used,
        remaining=total - used
    )

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    con = sqlite3.connect(get_active_db())
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM invites")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM invites WHERE used=1")
    used = cur.fetchone()[0]

    cur.execute(
        "SELECT token FROM invites WHERE used=1 ORDER BY rowid DESC LIMIT 20"
    )
    recent = [r[0] for r in cur.fetchall()]

    con.close()
    return jsonify(
        total=total,
        used=used,
        remaining=total - used,
        recent_used=recent
    )

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
