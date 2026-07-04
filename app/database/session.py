import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ☢️ লোকাল ডাটাবেসের জন্য ফিক্সড (Absolute) পাথ তৈরি করা হলো
# নিশ্চিত করবে যে পুরো প্রজেক্টে একটাই aura.db থাকবে, ডুপ্লিকেট হবে না
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'aura.db')}"

# লাইভ ডাটাবেস লিংক থাকলে সেটা নেবে, নাহলে লোকাল absolute sqlite নেবে
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB_URL)

# SQLAlchemy এর জন্য postgres:// কে postgresql:// করতে হয় (Render error fix)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite এর জন্য check_same_thread লাগে, Postgres এর লাগে না
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()