from werkzeug.security import generate_password_hash
import mysql.connector

# Database connection
connection = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',  # Your MySQL password
    database='project'
)

cursor = connection.cursor()

# Admin credentials
ADMIN_EMAIL = 'admin@medical.com'
ADMIN_PASSWORD = 'admin123'  # Change this to your desired password

# Hash the password
hashed_password = generate_password_hash(ADMIN_PASSWORD)

# Check if admin already exists
cursor.execute('SELECT user_id, is_admin FROM users WHERE email = %s', (ADMIN_EMAIL,))
existing = cursor.fetchone()

if existing:
    user_id, is_admin = existing
    if is_admin:
        # Update password
        cursor.execute('UPDATE users SET password = %s WHERE email = %s', 
                      (hashed_password, ADMIN_EMAIL))
        print(f"✅ Updated admin password for: {ADMIN_EMAIL}")
    else:
        # Make existing user admin
        cursor.execute('UPDATE users SET is_admin = 1, password = %s WHERE email = %s', 
                      (hashed_password, ADMIN_EMAIL))
        print(f"✅ Granted admin privileges to: {ADMIN_EMAIL}")
else:
    # Create new admin user
    cursor.execute('''
        INSERT INTO users (full_name, email, phone, age, gender, password, is_admin)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (
        'System Administrator',
        ADMIN_EMAIL,
        '9999999999',
        30,
        'Other',
        hashed_password,
        1  # is_admin = 1
    ))
    print(f"✅ Created new admin user: {ADMIN_EMAIL}")

connection.commit()
cursor.close()
connection.close()

print("\n" + "="*50)
print("🔐 ADMIN LOGIN CREDENTIALS")
print("="*50)
print(f"Email:    {ADMIN_EMAIL}")
print(f"Password: {ADMIN_PASSWORD}")
print("="*50)
print("\n📍 Admin Login URL: http://127.0.0.1:5000/admin-login")
print("✅ Setup complete!\n")