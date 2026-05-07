from face_auth import initialize_model
initialize_model()
from flask import Flask, render_template, request, Response, jsonify, session, redirect
import sqlite3
import os

from blockchain import Blockchain
from face_auth import generate_frames, recognize_user

app = Flask(__name__)
app.secret_key = "secret123"

blockchain = Blockchain()

# -------- ADMIN LOGIN --------
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# -------- CREATE FOLDER --------
if not os.path.exists('faces'):
    os.makedirs('faces')

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            face_path TEXT,
            voted INTEGER
        )
    ''')

    conn.commit()
    conn.close()

# -------- PRELOAD USERS --------
def preload_users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    users = ["prince", "rahul", "amit"]

    for user in users:
        face_path = f"faces/{user}.jpg"
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)",
                  (user, face_path, 0))

    conn.commit()
    conn.close()

# -------- INIT --------
init_db()
preload_users()

# -------- HOME --------
@app.route('/')
def index():
    return render_template('index.html')

# -------- CAMERA STREAM --------
@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# -------- FACE VOTING --------
@app.route('/auto_vote', methods=['POST'])
def auto_vote():

    user_id, conf = recognize_user()

    # ❌ Face not matched
    if user_id is None:
        return "ERROR: Face not recognized"

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # 🔐 Check if user exists in DB
    c.execute("SELECT voted FROM users WHERE id=?", (user_id,))
    result = c.fetchone()

    if not result:
        return "ERROR: Unauthorized user"

    # ❌ Already voted
    if result[0] == 1:
        return "ERROR: Already voted"

    vote = request.form['vote']

    # -------- BLOCKCHAIN --------
    previous_block = blockchain.get_previous_block()
    proof = blockchain.proof_of_work(previous_block['proof'])
    previous_hash = blockchain.hash(previous_block)

    blockchain.create_block(proof, previous_hash, data={
        'user': user_id,
        'vote': vote
    })

    # -------- UPDATE DATABASE --------
    c.execute("UPDATE users SET voted=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return f"SUCCESS:{user_id}"

# -------- RESULTS --------
@app.route('/results')
def results():
    votes = {}

    for block in blockchain.chain:
        data = block.get('data')
        if data:
            vote = data.get('vote')
            votes[vote] = votes.get(vote, 0) + 1

    return jsonify(votes)

# -------- ADMIN LOGIN --------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin'] = True
            return redirect('/secure-admin-portal')
        else:
            return render_template('admin_login.html', error="Invalid credentials")

    return render_template('admin_login.html')

# -------- ADMIN DASHBOARD (HIDDEN ROUTE) --------
@app.route('/secure-admin-portal')
def admin():
    if not session.get('admin'):
        return redirect('/admin_login')

    # Count votes (Python method - reliable)
    vote_count = 0
    for block in blockchain.chain:
        if block.get('data'):
            vote_count += 1

    return render_template("admin.html",
                           chain=blockchain.chain,
                           vote_count=vote_count)

# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

# -------- RUN --------
if __name__ == '__main__':
    app.run(debug=True)