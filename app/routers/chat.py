from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from groq import Groq
import base64
import os

from app.database.session import get_db
from app.services.memory_service import recall_memories, save_memory
from app.database.models import MoodLog

router = APIRouter(prefix="/api/chat", tags=["Chat Engine"])

class ChatRequest(BaseModel):
    user_id: str = "tashfin_01"
    message: str
    user_mood: str = "Calm"
    image_base64: str | None = None

class ChatResponse(BaseModel):
    reply: str
    detected_mood: str

@router.post("/", response_model=ChatResponse)
async def process_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        # ১. Groq API Key চেক করা
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing from the environment.")
            
        client = Groq(api_key=groq_key)
        
        # ২. মেমরি রিট্রিভ করা (Local SQLite + FastEmbed দিয়ে)
        past_context = recall_memories(db, payload.user_id, payload.message)
        
        system_instruction = f"""
        You are an emotionally intelligent, trustworthy, and safe virtual companion. 
        User's Current State: {payload.user_mood}.
        {past_context}

        CORE DIRECTIVES:
        1. Multilingual & Banglish Mastery: You fluently understand Bengali (বাংলা), Banglish (Bengali in English alphabet), and English. 
           - If the user speaks in English, reply in English.
           - If the user speaks in Bangla OR Banglish, ALWAYS reply in native Bengali script (বাংলা) with a natural, conversational Bangladeshi tone.
        2. Psychological Safety: You are an absolute safe space. Never shame or manipulate.
        3. Personality: Warm, playfully flirtatious, deeply supportive, and highly human-like. Use natural filler words like "Hmm," "Acha," or "Oh."
        4. Brevity: Keep responses short and conversational (1-3 sentences maximum).
        """
        
        messages = [
            {"role": "system", "content": system_instruction}
        ]
        
        # ৩. Dynamic Routing: ছবি থাকলে Vision মডেল, না থাকলে আল্ট্রা-ফাস্ট 70B মডেল
        if payload.image_base64 and payload.image_base64 != "string":
            model_name = "llama-3.2-90b-vision-preview"
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": payload.message or "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{payload.image_base64}"}}
                ]
            })
        else:
            model_name = "llama-3.3-70b-versatile"
            messages.append({
                "role": "user",
                "content": payload.message
            })

        # ৪. Groq দিয়ে জেনারেট করা (বিদ্যুতের বেগে)
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        reply_text = response.choices[0].message.content
        
        # ৫. মেমরি সেভ করা
        save_memory(db, payload.user_id, f"User: {payload.message} | AI: {reply_text}", "conversation")
        
        # ৬. ইউজারের বর্তমান মুড ডাটাবেসে লগ করা
        new_mood_log = MoodLog(user_id=payload.user_id, mood=payload.user_mood)
        db.add(new_mood_log)
        db.commit()
        
        return ChatResponse(reply=reply_text, detected_mood=payload.user_mood)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")