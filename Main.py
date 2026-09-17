from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime
import sqlite3

app = FastAPI(title="SuperApp Backend API", version="1.0")

DB_NAME = "superapp.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 100.0,
            esim_active BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            content TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_email TEXT,
            amount REAL,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PostCreate(BaseModel):
    user_id: int
    user_name: str
    content: str

class MoneyTransfer(BaseModel):
    sender_id: int
    receiver_email: str
    amount: float

@app.post("/register")
def register_user(user: UserRegister):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (user.name, user.email, user.password))
        conn.commit()
        return {"status": "success", "message": "تم إنشاء الحساب بنجاح!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل")
    finally:
        conn.close()

@app.post("/login")
def login_user(user: UserLogin):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, balance, esim_active FROM users WHERE email=? AND password=?", (user.email, user.password))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"status": "success", "user": {"id": result[0], "name": result[1], "email": result[2], "balance": result[3], "esim_active": bool(result[4])}}
    else:
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")

@app.get("/posts")
def get_posts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_name, content, created_at FROM posts ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "user_name": r[1], "content": r[2], "created_at": r[3]} for r in rows]

@app.post("/posts/create")
def create_post(post: PostCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO posts (user_id, user_name, content, created_at) VALUES (?, ?, ?, ?)", (post.user_id, post.user_name, post.content, now))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم نشر المنشور!"}

@app.post("/wallet/transfer")
def transfer_money(transfer: MoneyTransfer):
    if transfer.amount <= 0:
        raise HTTPException(status_code=400, detail="المبلغ غير صحيح")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE id=?", (transfer.sender_id,))
    sender = cursor.fetchone()
    if not sender or sender[0] < transfer.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ")
    cursor.execute("SELECT id FROM users WHERE email=?", (transfer.receiver_email,))
    receiver = cursor.fetchone()
    if not receiver:
        conn.close()
        raise HTTPException(status_code=404, detail="المستلم غير موجود")
    cursor.execute("UPDATE users SET balance = balance - ? WHERE id=?", (transfer.amount, transfer.sender_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE email=?", (transfer.amount, transfer.receiver_email))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"تم تحويل {transfer.amount}€ بنجاح!"}

@app.post("/esim/subscribe/{user_id}")
def subscribe_esim(user_id: int):
    cost = 19.99
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user or user[0] < cost:
        conn.close()
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ لشراء الاشتراك")
    cursor.execute("UPDATE users SET balance = balance - ?, esim_active = 1 WHERE id=?", (cost, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم تفعيل اشتراك الإنترنت بنجاح!"}

@app.get("/")
def home():
    return {"status": "online"}
    
