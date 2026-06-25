import os
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database.session import Base

ENV = os.getenv("ENV", "development")

# ডায়নামিক টাইপ সিলেকশন
if ENV == "production":
    from pgvector.sqlalchemy import Vector
    EmbeddingType = Vector(384)
else:
    EmbeddingType = JSON  # SQLite-এর জন্য JSON ফলব্যাক

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    companion_name = Column(String, default="Aura")
    relationship_level = Column(Integer, default=1)
    current_mood = Column(String, default="Calm")

class SemanticMemory(Base):
    __tablename__ = "semantic_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    memory_type = Column(String)
    content = Column(Text, nullable=False)
    embedding = Column(EmbeddingType)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MoodLog(Base):
    __tablename__ = "mood_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    mood = Column(String)  # (e.g., Calm, Stressed, Happy, Depressed)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())