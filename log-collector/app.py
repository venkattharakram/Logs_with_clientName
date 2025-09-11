#!/usr/bin/env python3
from flask import Flask, request
import os, psycopg2, requests
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time

app = Flask(__name__)

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "logsdb")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "logs_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "logs_pass")

ALLOWED_LEVELS = ("ERROR", "WARNING", "INFO", "DEBUG")

def get_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def init_db():
    sql = """
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        event_id TEXT UNIQUE,
        level TEXT,
        message TEXT,
        client_name TEXT,
        timestamp TIMESTAMP WITH TIME ZONE
    );
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()

def normalize_level(l):
    if not l:
        return "INFO"
    lvl = l.strip().upper()
    return lvl if lvl in ALLOWED_LEVELS else "INFO"

@app.route("/health")
def health():
    return {"status":"ok"}, 200

@app.route("/collect", methods=["POST"])
def collect():
    event = request.get_json()
    if not event:
        return {"error":"invalid payload"}, 400

    event_id = event.get("event_id") or str(int(time.time() * 1000))
    level = normalize_level(event.get("level"))
    message = event.get("message", "")
    client_name = event.get("client_name", "unknown")
    ts = event.get("timestamp")

    try:
        timestamp = datetime.fromisoformat(ts) if ts else datetime.utcnow()
    except Exception:
        timestamp = datetime.utcnow()

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (event_id, level, message, client_name, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """, (event_id, level, message, client_name, timestamp))
        conn.commit()
        cur.close()
        conn.close()

        return {"status":"ok"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/logs", methods=["GET"])
def get_logs():
    limit = int(request.args.get("limit", "500"))
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT event_id, level, message, client_name, timestamp
        FROM logs
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for r in rows:
        r['timestamp'] = r['timestamp'].isoformat()
    return {"logs": rows}, 200

@app.route("/analyze", methods=["GET"])
def analyze():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT level, COUNT(*) FROM logs GROUP BY level;")
    rows = cur.fetchall()
    stats = {r[0]: r[1] for r in rows}
    cur.close()
    conn.close()
    return {"counts": stats}, 200

if __name__ == "__main__":
    for i in range(10):
        try:
            init_db()
            break
        except Exception as e:
            print("Waiting for Postgres...", e)
            time.sleep(2)
    app.run(host="0.0.0.0", port=5002)

