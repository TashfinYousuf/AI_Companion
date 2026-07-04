import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# লাইভ ডাটাবেস লিংক থাকলে সেটা নেবে, নাহলে লোকাল sqlite নেবে
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aura.db")

# SQLAlchemy এর জন্য postgres:// কে postgresql:// করতে হয় (Render error fix)
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