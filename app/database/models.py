import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
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

    # --- NSFW/Adult Switch ---
    is_adult_mode = Column(Boolean, default=True) # ডিফল্ট True

class EmotionLog(Base):
    __tablename__ = "emotion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # 1. Core Emotions
    primary_emotion = Column(String)   # e.g., "Stress", "Joy", "Exhaustion"
    secondary_emotion = Column(String) # e.g., "Loneliness", "Hope", "Frustration"
    
    # 2. Emotional Intensity (1 to 10)
    intensity_score = Column(Integer, default=5) 
    
    # 3. What does the user need right now?
    # (e.g., 'Validation', 'Advice', 'Humor', 'Silence', 'Motivation')
    detected_need = Column(String, default="Listening") 
    
    # 4. Context/Trigger (Why are they feeling this way?)
    trigger_event = Column(String, nullable=True) # e.g., "Failed a test", "Long day at work"
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Emotion(Primary={self.primary_emotion}, Need={self.detected_need}, Intensity={self.intensity_score})>"

# --- THE PHASE A UPGRADE: Ultimate Memory Model ---
class SemanticMemory(Base):
    __tablename__ = "semantic_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Core Data
    content = Column(Text, nullable=False)
    embedding = Column(EmbeddingType)
    
    # --- Weighted System ---
    # Type: 'conversation', 'emotion', 'fact', 'goal', 'friction'
    memory_type = Column(String, default="conversation") 
    
    # 1 (Trivial) to 5 (Core Identity/Deep Emotion)
    importance_score = Column(Integer, default=1, index=True) 
    
    # --- Memory Decay System (Future-proofing) ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    access_count = Column(Integer, default=0) # কতবার এই মেমরিটি রিকল করা হয়েছে

    def __repr__(self):
        return f"<Memory(type={self.memory_type}, importance={self.importance_score})>"
    

# --- PHASE C: Autonomous Goal Engine ---
class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    title = Column(String, nullable=False) # e.g., "Maryland University Admission"
    description = Column(Text, nullable=True)
    status = Column(String, default="in_progress") # 'in_progress', 'completed', 'paused'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # রিলেশনশিপ: একটি গোলের আন্ডারে অনেকগুলো সাব-টাস্ক থাকবে
    tasks = relationship("SubTask", back_populates="goal", cascade="all, delete-orphan")

class SubTask(Base):
    __tablename__ = "subtasks"
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    
    title = Column(String, nullable=False) # e.g., "Research SOP format"
    is_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    goal = relationship("Goal", back_populates="tasks")


# --- PHASE 5: EPISODIC MEMORY & INTERNAL STATE ---
class SharedEpisode(Base):
    """
    এটি সাধারণ মেমরি নয়, এটি একটি সম্পূর্ণ স্মৃতি বা গল্প।
    যেমন: "The Night We Talked About University Doubts"
    """
    __tablename__ = "shared_episodes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    title = Column(String) # e.g., "Late night stress about exams"
    emotional_theme = Column(String) # e.g., "Vulnerability, Support"
    key_moments = Column(Text) # JSON list of what exactly happened
    impact_on_relationship = Column(String) # e.g., "Built immense trust"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuraInternalState(Base):
    """
    Aura-এর নিজস্ব মানসিক অবস্থা। সে কি এখন এক্সাইটেড? চিন্তিত? নাকি ফোকাসড?
    """
    __tablename__ = "aura_states"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    
    # Dynamic Personality Matrix (1 to 100)
    empathy_level = Column(Integer, default=80)
    curiosity_level = Column(Integer, default=70)
    playfulness_level = Column(Integer, default=50)
    
    # Emotional Overhang: আগের চ্যাটের রেশ
    residual_emotion = Column(String, default="Neutral") # e.g., "Concerned from last night"
    energy_level = Column(Integer, default=80) # 0 = exhausted, 100 = hyper
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())