from flask_mysqldb import MySQL
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

mysql = MySQL()

class User(UserMixin):
    def __init__(self, id, email, password, name, whatsapp, gender, age, is_admin, role):
        self.id = id
        self.email = email
        self.password = password
        self.name = name
        self.whatsapp = whatsapp
        self.gender = gender
        self.age = age
        self.is_admin = bool(is_admin)
        self.role = role
        
        
    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

def get_user_by_email(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password, name, whatsapp, gender, age, is_admin, role FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    cur.close()
    return User(*row) if row else None


def create_user(email, password, name, gender, age, whatsapp):
    hashed_password = generate_password_hash(password)
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users (email, password, name, gender, age, whatsapp) VALUES (%s, %s, %s, %s, %s, %s)",
                (email, hashed_password, name, gender, age, whatsapp))
    mysql.connection.commit()
    cur.close()

def save_history(user_id, city, temp, weather, rec):
    if isinstance(rec, list):
        # Convert list of dicts to plain text only
        rec = ", ".join([item['text'] for item in rec])
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO history (user_id, city, temp, weather, rec) VALUES (%s, %s, %s, %s, %s)",
        (user_id, city, temp, weather, rec)
    )
    mysql.connection.commit()
    cur.close()


def get_history(user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT city, temp, weather, rec, timestamp FROM history WHERE user_id = %s ORDER BY timestamp DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"city": row[0], "temp": row[1], "weather": row[2], "rec": row[3], "timestamp": row[4]}
        for row in rows
    ]
