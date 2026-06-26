from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.database.models import EmotionLog
from app.database.models import SemanticMemory
from app.database.models import Goal, SubTask

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/mood/{user_id}")
async def get_mood_analytics(user_id: str, db: Session = Depends(get_db)):
    try:
        logs = db.query(EmotionLog).filter(EmotionLog.user_id == user_id).order_by(EmotionLog.timestamp.desc()).limit(10).all()
        logs.reverse() 

        timeline = []
        for idx, log in enumerate(logs):
            timeline.append({
                "time": f"Chat {idx+1}",
                "intensity": log.intensity_score,
                "primary": log.primary_emotion,
                "need": log.detected_need
            })

        needs_counts = db.query(EmotionLog.detected_need, func.count(EmotionLog.id)).filter(EmotionLog.user_id == user_id).group_by(EmotionLog.detected_need).all()
        needs_map = {n: c for n, c in needs_counts}
        
        radar_categories = ["Validation", "Advice", "Space", "Motivation", "Listening", "Humor"]
        max_c = max(needs_map.values()) if needs_map else 1
        
        radar = []
        for cat in radar_categories:
            score = (needs_map.get(cat, 0) / max_c) * 100 if max_c > 0 else 0
            radar.append({"subject": cat, "A": score if score > 10 else 10, "fullMark": 100})

        history = [{"mood": log.primary_emotion} for log in logs]
        
        return {
            "history": history, 
            "timeline": timeline, 
            "radar": radar,
            "latest_need": logs[-1].detected_need if logs else "Listening",
            "latest_emotion": logs[-1].primary_emotion if logs else "Neutral"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/relationship/{user_id}")
async def get_relationship_status(user_id: str, db: Session = Depends(get_db)):
    try:
        # ইউজারের টোটাল কতগুলো কনভারসেশন সেভ হয়েছে তা গোনা
        msg_count = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).count()
        
        # লেভেল এবং প্রগ্রেস ক্যালকুলেশন
        if msg_count < 10:
            level, title, next_tier = 1, "Acquaintance", 10
        elif msg_count < 30:
            level, title, next_tier = 2, "Friend", 30
        elif msg_count < 60:
            level, title, next_tier = 3, "Close Confidant", 60
        elif msg_count < 100:
            level, title, next_tier = 4, "Partner", 100
        else:
            level, title, next_tier = 5, "Soulmate", msg_count # ম্যাক্স লেভেল
            
        progress_percentage = min(100, int((msg_count / next_tier) * 100))
        
        return {
            "user_id": user_id,
            "total_interactions": msg_count,
            "current_level": level,
            "title": title,
            "progress_to_next_level": progress_percentage
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))