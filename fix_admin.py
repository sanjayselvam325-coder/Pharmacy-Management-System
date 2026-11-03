# ============================================================
#  fix_admin.py — Run this ONCE to fix the login issue
#  It will:
#    1. Create the users table if it doesn't exist
#    2. Delete any broken admin accounts
#    3. Create a fresh admin account (admin / admin123)
#
#  How to run:  python fix_admin.py
# ============================================================

import mysql.connector
import hashlib

# ── CHANGE THESE TO MATCH YOUR MYSQL ──────────────────────
DB_USER     = 'root'
DB_PASSWORD = 'your_password'   # ← your MySQL password here
# ──────────────────────────────────────────────────────────
DB_HOST = 'localhost'
DB_NAME = 'pharmacy_db'
DB_PORT = 3306

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

print("\n" + "="*55)
print("  RxCore — Admin Account Fix Script")
print("="*55)

try:
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASSWORD, port=DB_PORT
    )
    cur = conn.cursor()

    # Make sure pharmacy_db exists
    cur.execute("CREATE DATABASE IF NOT EXISTS pharmacy_db")
    cur.execute("USE pharmacy_db")
    print("  [OK] Connected to pharmacy_db")

    # Create users table if it doesn't exist yet
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(100) NOT NULL UNIQUE,
            password   VARCHAR(255) NOT NULL,
            role       ENUM('admin','staff') DEFAULT 'staff',
            full_name  VARCHAR(150),
            email      VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  [OK] Users table is ready")

    # Remove any existing admin account (to start clean)
    cur.execute("DELETE FROM users WHERE username = 'admin'")
    deleted = cur.rowcount
    if deleted:
        print(f"  [OK] Removed {deleted} old admin account(s)")

    # Insert a brand new admin with a fresh hashed password
    new_hash = hash_pw('admin123')
    cur.execute(
        """INSERT INTO users (username, password, role, full_name, email)
           VALUES (%s, %s, 'admin', 'Administrator', 'admin@pharmacy.com')""",
        ('admin', new_hash)
    )
    conn.commit()
    print("  [OK] New admin account created")

    # Verify it was saved correctly
    cur.execute("SELECT id, username, role, password FROM users WHERE username='admin'")
    row = cur.fetchone()
    if row:
        stored_hash = row[3]
        test_hash   = hash_pw('admin123')
        match       = "✅ PASSWORD MATCHES" if stored_hash == test_hash else "❌ HASH MISMATCH"
        print(f"  [OK] Verification: {match}")
        print(f"       User ID  : {row[0]}")
        print(f"       Username : {row[1]}")
        print(f"       Role     : {row[2]}")

    conn.close()
    print("="*55)
    print("  Done! You can now log in with:")
    print("  Username : admin")
    print("  Password : admin123")
    print("="*55 + "\n")

    print("  Next steps:")
    print("  1. Run:   python app.py")
    print("  2. Open:  http://localhost:5000")
    print("  3. Login: admin / admin123\n")

except Exception as e:
    print(f"\n  [ERROR] {e}")
    print("\n  Please check:")
    print("  1. MySQL Workbench / MySQL service is running")
    print("  2. DB_PASSWORD is correct in this file\n")
