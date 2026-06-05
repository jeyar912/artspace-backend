import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv

# Load variables
load_dotenv()

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 15628)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "defaultdb"),
        ssl_disabled=True  # Hii inazima kuhitaji certificate (inasaidia kama huna ca.pem)
    )

def log_activity(text):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity_logs (log_text) VALUES (%s)", (text,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Logging error: {e}")

# ================= AUTHENTICATION ENDPOINTS =================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    role = data.get('role')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == 'admin':
            return jsonify({"success": False, "message": "Admins do not need registration"}), 400
        
        approved = 1 if role == 'user' else 0
        query = "INSERT INTO users (username, email, password, role, approved) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (username, email, password, role, approved))
        conn.commit()
        
        log_activity(f"New {role} registered: {username}")
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Registration successful"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": str(err)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    username = data.get('username')
    password = data.get('password')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE username = %s AND password = %s AND role = %s"
        cursor.execute(query, (username, password, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if role == 'artist' and not user['approved']:
                return jsonify({"success": False, "message": "Artist not approved yet"}), 401
            log_activity(f"User logged in: {username}")
            return jsonify({"success": True, "username": user['username'], "role": user['role']})
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ================= ARTWORKS ENDPOINTS =================

@app.route('/api/artworks', methods=['GET'])
def get_artworks():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM artworks")
        artworks = cursor.fetchall()
        for art in artworks:
            art['_id'] = str(art['id'])
            art['artist'] = art.get('artist_username')
            art['desc'] = art.get('description')
        cursor.close()
        conn.close()
        return jsonify(artworks)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ================= SERVER START =================

if __name__ == '__main__':
    # Tunatumia port ya Render, au 5000 kama haipo
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)