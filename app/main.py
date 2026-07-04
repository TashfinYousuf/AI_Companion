from dotenv import load_dotenv
# Load environment variables
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, voice, analytics
from app.database.session import engine, Base
from app.database import models
from app.database.models import SemanticMemory

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