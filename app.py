# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import MySQLdb
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_CONFIG, SECRET_KEY
import random, time

app = Flask(__name__)
app.secret_key = SECRET_KEY

def get_db():
    return MySQLdb.connect(
        host=DB_CONFIG["HOST"],
        user=DB_CONFIG["USER"],
        passwd=DB_CONFIG["PASSWORD"],
        db=DB_CONFIG["NAME"],
        charset="utf8mb4"
    )

def query_one(sql, params=()):
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(sql, params); row = cur.fetchone()
    cur.close(); db.close(); return row

def execute(sql, params=()):
    db = get_db(); cur = db.cursor()
    cur.execute(sql, params); db.commit()
    last_id = cur.lastrowid
    cur.close(); db.close(); return last_id

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    username = request.form.get("username")
    password = request.form.get("password")
    user = query_one("SELECT * FROM users WHERE username=%s", (username,))
    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("start_game"))
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    if query_one("SELECT id FROM users WHERE username=%s", (username,)):
        return render_template("login.html", error="Username taken")
    pwd_hash = generate_password_hash(password)
    execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, pwd_hash))
    return redirect(url_for("login"))

@app.route("/start")
def start_game():
    if "user_id" not in session:
        return redirect(url_for("login"))
    session_id = execute("INSERT INTO game_sessions (user_id) VALUES (%s)", (session["user_id"],))
    session["session_id"] = session_id
    return render_template("game.html")

def pick_question(category=None, difficulty=None):
    sql = "SELECT * FROM questions"
    params = []
    filters = []
    if category:
        filters.append("category=%s"); params.append(category)
    if difficulty:
        filters.append("difficulty=%s"); params.append(difficulty)
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY RAND() LIMIT 1"
    return query_one(sql, tuple(params))

@app.route("/api/question")
def api_question():
    if "session_id" not in session:
        return jsonify({"error":"no session"}), 403
    category = request.args.get("category")  # optional
    difficulty = request.args.get("difficulty")  # optional
    q = pick_question(category, difficulty)
    if not q:
        return jsonify({"error":"no questions"}), 404
    payload = {
        "id": q["id"],
        "text": q["question_text"],
        "options": {
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"]
        },
        "category": q["category"],
        "difficulty": q["difficulty"],
        "image_url": q["image_url"]
    }
    session["q_start_ts"] = int(time.time() * 1000)
    return jsonify(payload)

def score_for(difficulty, seconds, correct):
    base = {"Easy":10, "Medium":20, "Hard":30}.get(difficulty, 10)
    time_bonus = max(0, 10 - int(seconds))
    return base + time_bonus if correct else 0

@app.route("/api/answer", methods=["POST"])
def api_answer():
    data = request.get_json()
    qid = data.get("question_id")
    selected = data.get("selected_option")
    q = query_one("SELECT correct_option, difficulty FROM questions WHERE id=%s", (qid,))
    if not q:
        return jsonify({"error":"invalid question"}), 400
    end_ts = int(time.time() * 1000)
    start_ts = session.get("q_start_ts", end_ts)
    elapsed_ms = end_ts - start_ts
    is_correct = (selected == q["correct_option"])
    seconds = elapsed_ms / 1000.0
    points = score_for(q["difficulty"], seconds, is_correct)

    execute("""INSERT INTO answers (session_id, question_id, selected_option, is_correct, time_taken_ms)
               VALUES (%s,%s,%s,%s,%s)""",
            (session["session_id"], qid, selected, is_correct, int(elapsed_ms)))

    # update session total
    execute("""UPDATE game_sessions SET total_score = total_score + %s WHERE id=%s""",
            (points, session["session_id"]))

    return jsonify({"correct": is_correct, "points": points})

@app.route("/end")
def end_game():
    if "session_id" not in session:
        return redirect(url_for("index"))
    execute("UPDATE game_sessions SET ended_at=NOW() WHERE id=%s", (session["session_id"],))
    # persist to scores table for leaderboard
    sess = query_one("SELECT user_id, total_score FROM game_sessions WHERE id=%s", (session["session_id"],))
    execute("INSERT INTO scores (user_id, score) VALUES (%s,%s)", (sess["user_id"], sess["total_score"]))
    sid = session.pop("session_id", None)
    return redirect(url_for("leaderboard"))

@app.route("/leaderboard")
def leaderboard():
    rows = []
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""SELECT u.username, s.score, s.created_at
                   FROM scores s JOIN users u ON s.user_id=u.id
                   ORDER BY s.score DESC, s.created_at ASC LIMIT 20""")
    rows = cur.fetchall(); cur.close(); db.close()
    return render_template("leaderboard.html", rows=rows)
if __name__ == "__main__":
    app.run(debug=True)