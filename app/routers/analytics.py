from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.database.models import EmotionLog
from app.database.models import SemanticMemory
from app.database.models import Goal, SubTask
from app.services.dream_service import process_nightly_dreams

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# ================================================
# 📊 MOOD & GRAPH ENGINE (WITH HEAVY DEBUGGER)
# ================================================
@router.get("/mood/{user_id}")
async def get_mood_analytics(user_id: str, db: Session = Depends(get_db)):
    try:
        print(f"\n🛠️ [DEBUG ANALYTICS] Fetching mood for user: {user_id}")
        logs = db.query(EmotionLog).filter(EmotionLog.user_id == user_id).order_by(EmotionLog.timestamp.desc()).limit(10).all()
        print(f"🛠️ [DEBUG ANALYTICS] Total logs fetched: {len(logs)}")
        
        if not logs:
            return {"history": [], "timeline": [{"time": "Now", "intensity": 5, "primary": "Neutral", "need": "Listening"}], "radar": [], "latest_need": "Listening", "latest_emotion": "Neutral"}

        logs.reverse() 

        timeline = []
        for idx, log in enumerate(logs):
            timeline.append({
                "time": f"Chat {idx+1}",
                "intensity": int(log.intensity_score) if log.intensity_score else 5,
                "primary": log.primary_emotion,
                "need": log.detected_need
            })

        # --- DEBUGGING RADAR CALCULATION ---
        needs_counts = db.query(EmotionLog.detected_need, func.count(EmotionLog.id)).filter(EmotionLog.user_id == user_id).group_by(EmotionLog.detected_need).all()
        print(f"🛠️ [DEBUG ANALYTICS] 1. Raw needs_counts from DB: {needs_counts}")
        
        needs_map = {}
        for n, c in needs_counts:
            if n:
                for part in str(n).replace("'", "").replace('"', '').split(','):
                    clean_part = part.strip().title()
                    needs_map[clean_part] = needs_map.get(clean_part, 0) + c
                    
        print(f"🛠️ [DEBUG ANALYTICS] 2. Parsed needs_map: {needs_map}")

        radar_categories = ["Validation", "Advice", "Space", "Motivation", "Listening", "Humor"]
        valid_counts = [needs_map.get(cat, 0) for cat in radar_categories]
        print(f"🛠️ [DEBUG ANALYTICS] 3. Valid counts mapped to categories: {valid_counts}")
        
        max_c = max(valid_counts) if max(valid_counts) > 0 else 1
        
        radar = []
        for cat in radar_categories:
            score = int((needs_map.get(cat, 0) / max_c) * 100)
            radar.append({"subject": cat, "A": max(15, score), "fullMark": 100})

        print(f"🛠️ [DEBUG ANALYTICS] 4. FINAL RADAR ARRAY TO FRONTEND:\n{radar}\n")
        # -----------------------------------

        history = [{"mood": log.primary_emotion} for log in logs]
        
        return {
            "history": history, 
            "timeline": timeline, 
            "radar": radar,
            "latest_need": logs[-1].detected_need if logs else "Listening",
            "latest_emotion": logs[-1].primary_emotion if logs else "Neutral"
        }
    except Exception as e:
        import traceback
        print(f"⚠️ [DEBUG ANALYTICS ERROR]:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    

# ====================================
# 💖 RELATIONSHIP LEVEL ENGINE
# ====================================
@router.get("/relationship/{user_id}")
async def get_relationship_status(user_id: str, db: Session = Depends(get_db)):
    try:
        msg_count = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).count()
        
        if msg_count < 10:
            level, title, next_tier = 1, "Acquaintance", 10
        elif msg_count < 30:
            level, title, next_tier = 2, "Friend", 30
        elif msg_count < 60:
            level, title, next_tier = 3, "Close Confidant", 60
        elif msg_count < 100:
            level, title, next_tier = 4, "Partner", 100
        else:
            level, title, next_tier = 5, "Soulmate", msg_count 
            
        progress_percentage = min(100, int((msg_count / next_tier) * 100))
        
        return {
            "user_id": user_id,
            "total_interactions": msg_count,
            "current_level": level,
            "title": title,
            "progress_to_next_level": progress_percentage
        } #[cite: 5]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# 🎯 GOALS ENGINE
# ========================
@router.get("/goals/{user_id}")
async def get_user_goals(user_id: str, db: Session = Depends(get_db)):
    try:
        goals = db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.created_at.desc()).all()
        
        response_data = []
        for goal in goals:
            tasks = db.query(SubTask).filter(SubTask.goal_id == goal.id).all()
            completed_tasks = sum(1 for t in tasks if t.is_completed)
            progress = int((completed_tasks / len(tasks)) * 100) if tasks else 0
            
            response_data.append({
                "id": goal.id,
                "title": goal.title,
                "description": goal.description,
                "status": goal.status,
                "progress": progress,
                "tasks": [{"id": t.id, "title": t.title, "is_completed": t.is_completed} for t in tasks]
            })
            
        return response_data #[cite: 5]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ================================
# 💤 DREAM TRIGGER ENGINE
# ================================
@router.post("/trigger-dream/{user_id}")
async def trigger_dream(user_id: str, db: Session = Depends(get_db)):
    result = process_nightly_dreams(db, user_id)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return result #[cite: 5]