from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import MoodLog

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard"])

@router.get("/mood/{user_id}")
async def get_mood_history(user_id: str, db: Session = Depends(get_db)):
    try:
        # ডাটাবেস থেকে ওই ইউজারের সর্বশেষ ৭টি মুড লগ টেনে আনা (Desc order)
        logs = db.query(MoodLog).filter(
            MoodLog.user_id == user_id
        ).order_by(
            MoodLog.timestamp.desc()
        ).limit(7).all()
        
        if not logs:
            return {"user_id": user_id, "history": []}
            
        # ফ্রন্টএন্ডের চার্টের জন্য ডেটা ফরম্যাট করা
        formatted_history = [
            {
                "mood": log.mood, 
                "time": log.timestamp.strftime("%Y-%m-%d %H:%M") # সুন্দর টাইম ফরম্যাট
            } 
            for log in logs
        ]
        
        # গ্রাফে দেখানোর জন্য ডেটা উল্টে দেওয়া (পুরনো থেকে নতুন)
        return {"user_id": user_id, "history": formatted_history[::-1]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))