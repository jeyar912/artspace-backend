import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Unganisha na database yako ya Aiven kwa kutumia .env yako iliyopo tayari
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 15628)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "defaultdb"),
    ssl_ca="",
    ssl_verify_identity=False
)

cursor = conn.cursor()

# Hapa sasa tunaingiza Admin moja kwa moja kwa kutumia kodi za Python zilizopo kwenye app.py yako
try:
    query = """INSERT INTO users (username, email, password, role, approved) 
               VALUES (%s, %s, %s, %s, %s)"""
    cursor.execute(query, ('admin', 'admin@artspace.com', 'admin123', 'admin', 1))
    conn.commit()
    print("✅ Admin 'admin' na password 'admin123' ameingizwa kikamilifu kwenye Aiven MySQL!")
except Exception as e:
    print(f"❌ Error: {e}")

cursor.close()
conn.close()