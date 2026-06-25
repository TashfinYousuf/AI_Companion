import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV", "development")

if ENV == "development" or not DATABASE_URL:
    # SQLite for local dev
    DB_PATH = os.path.join(os.path.dirname(__file__), "../../local.db")
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False}
    )
    print("[INFO] Using local SQLite database for development")
else:
    # PostgreSQL for Production
    engine = create_engine(DATABASE_URL)
    print("[INFO] Using PostgreSQL (Supabase)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()