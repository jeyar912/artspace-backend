from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)  # Enables cross-origin execution for frontends

# Database configuration helper for Aiven Cloud
def get_db_connection():
    return mysql.connector.connect(
        host="mysql-756dc3-mwinyijunior1976-2f0f.f.aivencloud.com",
        port=15628,
        user="avnadmin",
        password="AVNS_aYHaYKtBMmf7g-KFGMc",  # 👈 Paste your long Aiven password string here
        database="defaultdb",
        ssl_ca="",  # Leaving this empty string forces mysql.connector to initiate TLS/SSL encryption
        ssl_verify_identity=False  # Required for clean cloud handshake without local file verification
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
        
        # Admins do not auto register
        if role == 'admin':
            return jsonify({"success": False, "message": "Admins do not need registration"}), 400
        
        # Artist approval default is false (0), user approval default is true (1)
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM users WHERE username = %s AND password = %s AND role = %s"
    cursor.execute(query, (username, password, role))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if user:
        if role == 'artist' and not user['approved']:
            return jsonify({"success": False, "message": "Artist not approved yet by Admin"}), 401
        
        log_activity(f"User logged in: {username} ({role})")
        return jsonify({"success": True, "username": user['username'], "role": user['role']})
    
    return jsonify({"success": False, "message": "Invalid credentials or unapproved account"}), 401

# ================= ARTIST INTERFACES =================

@app.route('/api/artists', methods=['GET'])
def get_artists():
    username_filter = request.args.get('username')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if username_filter:
        cursor.execute("SELECT * FROM users WHERE role = 'artist' AND username = %s", (username_filter,))
    else:
        cursor.execute("SELECT * FROM users WHERE role = 'artist'")
        
    artists = cursor.fetchall()
    
    for artist in artists:
        # Remap ID to match frontend expected string representation '_id'
        artist['_id'] = str(artist['id'])
        artist['approved'] = bool(artist['approved'])
        
        # Fetch Types
        cursor.execute("SELECT art_type FROM artist_art_types WHERE user_id = %s", (artist['id'],))
        artist['artTypes'] = [row['art_type'] for row in cursor.fetchall()]
        
        # Fetch Payments
        cursor.execute("SELECT payment_method FROM artist_payments WHERE user_id = %s", (artist['id'],))
        artist['paymentMethods'] = [row['payment_method'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return jsonify(artists)

@app.route('/api/artist/<int:id>', methods=['PUT'])
def update_artist(id):
    data = request.json
    phone = data.get('phone')
    address = data.get('address')
    website = data.get('website')
    art_types = data.get('artTypes', [])
    payment_methods = data.get('paymentMethods', [])
    profile_pic = data.get('profilePic')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update flat variables
        update_query = """UPDATE users SET phone = %s, address = %s, website = %s, profilePic = %s 
                          WHERE id = %s AND role = 'artist'"""
        cursor.execute(update_query, (phone, address, website, profile_pic, id))
        
        # Refresh Multi-value lists
        cursor.execute("DELETE FROM artist_art_types WHERE user_id = %s", (id,))
        for t in art_types:
            if t: cursor.execute("INSERT INTO artist_art_types (user_id, art_type) VALUES (%s, %s)", (id, t))
            
        cursor.execute("DELETE FROM artist_payments WHERE user_id = %s", (id,))
        for p in payment_methods:
            if p: cursor.execute("INSERT INTO artist_payments (user_id, payment_method) VALUES (%s, %s)", (id, p))
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/artist/approve/<int:id>', methods=['POST'])
def approve_artist(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT username FROM users WHERE id = %s", (id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "message": "Artist target not found"}), 404
            
        cursor.execute("UPDATE users SET approved = 1 WHERE id = %s", (id,))
        conn.commit()
        
        log_activity(f"Admin approved artist profile: {user['username']}")
        
        cursor.close()
        conn.close()
        return jsonify({"success": True, "username": user['username']})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# ================= USER ENDPOINTS =================

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM users WHERE role = 'user'")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

# ================= ARTWORKS MANAGEMENT ENDPOINTS =================

@app.route('/api/artworks', methods=['GET'])
def get_artworks():
    artist_filter = request.args.get('artist')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if artist_filter:
        cursor.execute("SELECT * FROM artworks WHERE artist_username = %s", (artist_filter,))
    else:
        cursor.execute("SELECT * FROM artworks")
        
    artworks = cursor.fetchall()
    
    for art in artworks:
        art['_id'] = str(art['id'])
        art['artist'] = art['artist_username']
        art['desc'] = art['description']
        
        # Fetch child Tags
        cursor.execute("SELECT tag FROM artwork_tags WHERE artwork_id = %s", (art['id'],))
        art['tags'] = [r['tag'] for r in cursor.fetchall()]
        
        # Fetch structural comments
        cursor.execute("SELECT username as user, text FROM comments WHERE artwork_id = %s", (art['id'],))
        art['comments'] = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(artworks)

@app.route('/api/artworks', methods=['POST'])
def upload_artwork():
    data = request.json
    artist = data.get('artist')
    title = data.get('title')
    art_type = data.get('type')
    desc = data.get('desc')
    price = data.get('price')
    image = data.get('image')
    tags = data.get('tags', [])

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO artworks (artist_username, title, type, description, price, image) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (artist, title, art_type, desc, price, image))
        artwork_id = cursor.lastrowid
        
        for tag in tags:
            if tag: cursor.execute("INSERT INTO artwork_tags (artwork_id, tag) VALUES (%s, %s)", (artwork_id, tag))
            
        conn.commit()
        log_activity(f"Artwork uploaded: '{title}' by {artist}")
        
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# ================= INTERACTIONS (LIKES / COMMENTS) =================

@app.route('/api/artworks/<int:id>/like', methods=['POST'])
def like_artwork(id):
    data = request.json
    username = data.get('username')  # Passed from user interaction
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Register into user specific tracking layout
        cursor.execute("INSERT IGNORE INTO user_likes (username, artwork_id) VALUES (%s, %s)", (username, id))
        
        # Increment parent metric cache counter
        cursor.execute("UPDATE artworks SET likes = likes + 1 WHERE id = %s", (id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/artworks/<int:id>/comment', methods=['POST'])
def comment_artwork(id):
    data = request.json
    username = data.get('username')
    text = data.get('text')

    if not text:
        return jsonify({"success": False, "message": "Text block cannot be empty"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO comments (artwork_id, username, text) VALUES (%s, %s, %s)", (id, username, text))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# ================= ADMINISTRATIVE DATA LOGS =================

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT log_text FROM activity_logs ORDER BY id ASC")
    logs = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(logs)

if __name__ == '__main__':
    # Run server locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)