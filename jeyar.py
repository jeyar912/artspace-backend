from flask import Flask, request, jsonify
from flask_cors import CORS
import base64

app = Flask(__name__)
CORS(app)

# ===== Data storage (temporary in-memory) =====
users = []
artists = []
artworks = []
logs = []

admin_user = {"username":"admin","email":"admin@art.com","password":"admin123","role":"admin"}

# ===== Helper =====
def find_user(email):
    for u in users + artists + [admin_user]:
        if u['email'] == email:
            return u
    return None

# ====== Auth API =====
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if find_user(email):
        return jsonify({"error":"Email already registered"}), 400

    if role == "artist":
        artists.append({"id":len(artists)+1,"username":username,"email":email,"password":password,"role":"artist","approved":False,"artTypes":[],"paymentMethods":[],"profilePic":"","phone":"","address":"","website":""})
        logs.append(f"New artist registered: {username}")
        return jsonify({"success":True,"message":"Artist registered! Waiting approval."})
    else:
        users.append({"id":len(users)+1,"username":username,"email":email,"password":password,"role":"user"})
        logs.append(f"New user registered: {username}")
        return jsonify({"success":True,"message":"User registered successfully!"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = find_user(email)
    if not user or user['password'] != password:
        return jsonify({"error":"Invalid email or password"}), 400

    return jsonify({"role":user['role'], "username":user['username'], "email":user['email']})

# ====== Gallery API =====
@app.route('/artworks', methods=['GET'])
def get_artworks():
    result = []
    for art in artworks:
        artist = next((a for a in artists if a['username']==art['artist']),{})
        result.append({
            "id": art['id'],
            "title": art['title'],
            "artist": art['artist'],
            "desc": art['desc'],
            "type": art['type'],
            "tags": art['tags'],
            "price": art['price'],
            "image": art['image'],
            "likes": art.get('likes',0),
            "comments": art.get('comments',[]),
            "paymentMethods": artist.get('paymentMethods',[])
        })
    return jsonify(result)

@app.route('/artists', methods=['GET'])
def get_artists():
    return jsonify([{"username":a['username'], "email":a['email'], "phone":a['phone'], "address":a['address'], "paymentMethods":a['paymentMethods']} for a in artists])

# ====== Like & Comment =====
@app.route('/artworks/like/<int:art_id>', methods=['POST'])
def like_art(art_id):
    art = next((a for a in artworks if a['id']==art_id),None)
    if art:
        art['likes'] = art.get('likes',0)+1
        logs.append(f"Artwork liked: {art['title']}")
        return jsonify({"success":True})
    return jsonify({"error":"Artwork not found"}),404

@app.route('/artworks/comment/<int:art_id>', methods=['POST'])
def comment_art(art_id):
    art = next((a for a in artworks if a['id']==art_id),None)
    if not art: return jsonify({"error":"Artwork not found"}),404
    data = request.get_json()
    txt = data.get('text')
    user = data.get('user')
    art.setdefault('comments',[]).append({"user":user,"text":txt})
    logs.append(f"New comment by {user} on {art['title']}")
    return jsonify({"success":True})

# ====== Admin API =====
@app.route('/admin/dashboard')
def admin_dashboard():
    return jsonify({
        "total_artists":len(artists),
        "approved_artists":len([a for a in artists if a['approved']]),
        "total_users":len(users),
        "total_artworks":len(artworks),
        "total_likes":sum(a.get('likes',0) for a in artworks),
        "total_comments":sum(len(a.get('comments',[])) for a in artworks),
        "artists":artists,
        "users":users,
        "artworks":artworks,
        "logs":logs
    })

@app.route('/admin/approve_artist/<int:artist_id>', methods=['POST'])
def approve_artist(artist_id):
    artist = next((a for a in artists if a['id']==artist_id),None)
    if not artist: return jsonify({"error":"Artist not found"}),404
    artist['approved']=True
    logs.append(f"Artist approved: {artist['username']}")
    return jsonify({"success":True,"message":f"{artist['username']} approved"})

# ===== Artist Profile & Upload =====
@app.route('/artist/profile/<username>', methods=['GET','POST'])
def artist_profile(username):
    artist = next((a for a in artists if a['username']==username),None)
    if not artist: return jsonify({"error":"Artist not found"}),404
    if request.method=='POST':
        data = request.get_json()
        for k in ['phone','address','website','artTypes','paymentMethods','profilePic']:
            artist[k] = data.get(k, artist.get(k))
        logs.append(f"Artist profile updated: {username}")
        return jsonify({"success":True})
    return jsonify(artist)

@app.route('/artist/upload_art/<username>', methods=['POST'])
def artist_upload(username):
    artist = next((a for a in artists if a['username']==username),None)
    if not artist: return jsonify({"error":"Artist not found"}),404
    data = request.get_json()
    artworks.append({
        "id":len(artworks)+1,
        "artist":username,
        "title":data['title'],
        "desc":data['desc'],
        "type":data['type'],
        "tags":data['tags'],
        "price":data['price'],
        "image":data['image'],
        "likes":0,
        "comments":[]
    })
    logs.append(f"Artwork uploaded: {data['title']} by {username}")
    return jsonify({"success":True})

@app.route('/artist/myarts/<username>')
def artist_myarts(username):
    return jsonify([a for a in artworks if a['artist']==username])

# ===== Run server =====
if __name__=='__main__':
    import os
    if __name__=='__main__':
        port=int(os.environment.get("PORT",5000))
        app.run(host='0.0.0.0',port=port)