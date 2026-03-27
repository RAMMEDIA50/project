from flask import Flask, request, jsonify, render_template, Response
import sqlite3
import csv
import io
from datetime import datetime

app = Flask(__name__, template_folder="templates")

# ---------- DATABASE ----------
def connect():
    return sqlite3.connect("db.sqlite3")

def init_db():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS contributions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        amount REAL,
        week INTEGER,
        month TEXT
    )
    """)

    # NEW: FINES TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS fines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        amount REAL,
        reason TEXT,
        date TEXT
    )
    """)

    conn.commit()

    # CREATE ADMIN
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                  ("admin", "1234", "admin"))
        conn.commit()

    conn.close()

init_db()

# ---------- PAGES ----------
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("index.html")

# ---------- AUTH ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    conn = connect()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (data["username"], data["password"]))

    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({"status": "success", "role": user[3]})
    return jsonify({"status": "fail"})

# ---------- MEMBERS ----------
@app.route("/members", methods=["GET"])
def get_members():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM members")
    data = c.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/add-member", methods=["POST"])
def add_member():
    data = request.json
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO members(name) VALUES(?)", (data["name"],))
    conn.commit()
    conn.close()
    return jsonify({"msg": "added"})

# NEW: DELETE MEMBER
@app.route("/delete-member/<int:id>", methods=["DELETE"])
def delete_member(id):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "deleted"})

# ---------- CONTRIBUTIONS ----------
@app.route("/add-contribution", methods=["POST"])
def add_contribution():
    data = request.json
    conn = connect()
    c = conn.cursor()

    c.execute("""
    INSERT INTO contributions(member_id,amount,week,month)
    VALUES(?,?,?,?)
    """, (data["member_id"], data["amount"], data["week"], data["month"]))

    conn.commit()
    conn.close()
    return jsonify({"msg": "saved"})

@app.route("/contributions", methods=["GET"])
def get_contributions():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    SELECT contributions.id, members.name, amount, week, month, member_id
    FROM contributions
    JOIN members ON members.id = contributions.member_id
    """)

    data = c.fetchall()
    conn.close()
    return jsonify(data)

# ---------- FINES ----------
@app.route("/add-fine", methods=["POST"])
def add_fine():
    data = request.json
    conn = connect()
    c = conn.cursor()

    c.execute("""
    INSERT INTO fines(member_id,amount,reason,date)
    VALUES(?,?,?,?)
    """, (data["member_id"], data["amount"], data["reason"], datetime.now().strftime("%Y-%m-%d")))

    conn.commit()
    conn.close()
    return jsonify({"msg": "fine added"})

@app.route("/fines", methods=["GET"])
def get_fines():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    SELECT members.name, amount, reason, date
    FROM fines
    JOIN members ON members.id = fines.member_id
    """)

    data = c.fetchall()
    conn.close()
    return jsonify(data)

# ---------- REPORT DOWNLOAD ----------
@app.route("/download-report/<month>")
def download_report(month):
    conn = connect()
    c = conn.cursor()

    c.execute("""
    SELECT members.name, SUM(amount)
    FROM contributions
    JOIN members ON members.id = contributions.member_id
    WHERE month=?
    GROUP BY members.name
    """, (month,))

    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Member", "Total Contribution"])
    for row in rows:
        writer.writerow(row)

    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename={month}_report.csv"})

# ---------- RUN ----------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)