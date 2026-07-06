from dotenv import load_dotenv
# Load environment variables
load_dotenv()

import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, voice, analytics
from app.database.session import engine, Base
from app.database import models
from app.database.models import SemanticMemory
from pydantic import BaseModel

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"[WARNING] Could not run create_all: {e}")

app = FastAPI(title="Companion OS", version="1.0")

# CORS Middleware (ফ্রন্টএন্ডকে ব্যাকএন্ডের সাথে কথা বলার পারমিশন দেয়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # প্রোডাকশনে ফ্রন্টএন্ডের ডোমেইন
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the chat routing logic
app.include_router(chat.router)
app.include_router(voice.router, tags=["Voice"])
app.include_router(analytics.router)

@app.get("/")
async def root():
    return {"message": "Aura Companion OS is running perfectly. Safe space activated."}


# 1. Auto-create permanent chat table
def init_permanent_chat_db():
    with sqlite3.connect("local.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS permanent_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            image_url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
init_permanent_chat_db()

# 2. Schema for receiving chat data
class SaveMessage(BaseModel):
    user_id: str
    role: str
    content: str
    image_url: str | None = None

# 3. API to SAVE message from any device
@app.post("/api/chat/save")
def save_chat_message(msg: SaveMessage):
    with sqlite3.connect("local.db") as conn:
        conn.execute("INSERT INTO permanent_chats (user_id, role, content, image_url) VALUES (?, ?, ?, ?)",
                     (msg.user_id, msg.role, msg.content, msg.image_url))
    return {"status": "saved"}

# 4. API to FETCH history from any device
@app.get("/api/chat/history/{user_id}")
def get_permanent_history(user_id: str):
    with sqlite3.connect("local.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, image_url FROM permanent_chats WHERE user_id = ? ORDER BY id ASC", (user_id,))
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"], "imageUrl": r["image_url"]} for r in rows]