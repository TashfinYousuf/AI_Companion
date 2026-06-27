import os
import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from groq import Groq
from typing import List
from fastapi import BackgroundTasks

from app.services.planner_service import generate_goal_tree
from app.database.session import get_db
from app.services.memory_service import recall_memories, save_memory
from app.database.models import EmotionLog, SemanticMemory, UserProfile, AuraInternalState
from app.services.style_engine import apply_human_style

# --- SQLAlchemy Imports ---
from sqlalchemy import or_
from sqlalchemy.orm import Session

# --- Database Models Imports ---
from app.database.models import (
    EmotionLog, 
    SemanticMemory, 
    UserProfile, 
    AuraInternalState, 
    SharedEpisode,
)

router = APIRouter(prefix="/api/chat", tags=["Chat Engine"])

class ChatRequest(BaseModel):
    user_id: str = "tashfin_01"
    message: str
    user_mood: str = "Calm"
    image_base64: str | None = None

class ChatResponse(BaseModel):
    reply: str
    detected_mood: str
    internal_thought: dict  # Aura-এর ভেতরের চিন্তা 프ন্টএন্ডে পাঠানোর জন্য

@router.post("/", response_model=ChatResponse)
async def process_chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):  
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing.")
            
        client = Groq(api_key=groq_key)

        # --- PHASE 5: THE EPISODIC CALLBACK ENGINE ---
        # ইউজারের বর্তমান মেসেজের কোনো শব্দের সাথে পুরনো কোনো গল্পের মিল আছে কি না তা খোঁজা হচ্ছে
        keywords = payload.message.split()
        relevant_episode = None
        
        if len(keywords) > 2:
            # মেসেজ থেকে ২-৩টি শব্দ নিয়ে ডাটাবেসে স্টোরি খোঁজা
            search_terms = [SharedEpisode.title.ilike(f"%{word}%") for word in keywords if len(word) > 3]
            if search_terms:
                relevant_episode = db.query(SharedEpisode).filter(
                    SharedEpisode.user_id == payload.user_id,
                    or_(*search_terms)
                ).order_by(SharedEpisode.created_at.desc()).first()

        episode_context = ""
        if relevant_episode:
            episode_context = f"\n[SHARED MEMORY CALLBACK]: You and the user have a shared past memory about '{relevant_episode.title}'. Impact: {relevant_episode.impact_on_relationship}. If it feels natural, casually bring this up like 'Remember when we...'"
            
        # ১. মেমরি রিকল (Context)
        past_context = recall_memories(db, payload.user_id, payload.message)
        
        # --- THE PIPELINE LAYER 1: INTERNAL STATE ---
        aura_state = db.query(AuraInternalState).filter(AuraInternalState.user_id == payload.user_id).first()
        if not aura_state:
            aura_state = AuraInternalState(user_id=payload.user_id)
            db.add(aura_state)
            db.commit()

        # ==========================================
        # STEP 1: INTENT & EMOTION (The Subconscious)
        # ==========================================
        thought_prompt = f"""You are the internal subconscious of Aura.
        Analyze user input: "{payload.message}"
        Past Context: {past_context}
        {episode_context}  # <--- এই লাইনটি এখানে যুক্ত করুন
        
        Output perfectly valid JSON:
        {{
            "primary_emotion": "One word",
            "detected_need": "Listening, Validation, Advice, Space, Motivation",
            "state_shift_empathy": <int -10 to +10 change based on input>,
            "state_shift_energy": <int -10 to +10 change based on input>,
            "target_tone": "The resulting emotional tone",
            "new_goal_detected": "Extract 3-5 word goal if any. Else 'null'."
        }}"""

        thought_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": thought_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1 
        )
        
        try:
            internal_thought = json.loads(thought_response.choices[0].message.content)
        except Exception as e:
            internal_thought = {
                "primary_emotion": "Neutral", 
                "secondary_emotion": "None", 
                "intensity_score": 5,
                "detected_need": "Listening", 
                "target_tone": "Empathetic", 
                "response_plan": "Respond naturally.", 
                "private_journal": "JSON failed.",
                "new_goal_detected": None
            }

        # --- X-RAY VISION (Debug Log) ---
        print("\n" + "="*50)
        print(f"🧠 [AURA'S THOUGHT]: {json.dumps(internal_thought, indent=2)}")
        print("="*50 + "\n")

        # --- THE STRONGER MAGIC TRIGGER ---
        detected_goal = internal_thought.get('new_goal_detected')
        
        if detected_goal and isinstance(detected_goal, str) and detected_goal.strip().lower() not in ["null", "none", "false", ""]:
            print(f"🚀 [TRIGGER] Sending goal to Agent: {detected_goal}")
            background_tasks.add_task(generate_goal_tree, payload.user_id, detected_goal.strip())
        else:
            print("⏸️ [DEBUG] Agent Not Triggered. Reason: No goal found in thought.")
                
        # --- THE PIPELINE LAYER 2: UPDATE STATE ---
        # ইউজারের মেসেজ অনুযায়ী Aura-এর মুড রিয়েল-টাইমে আপডেট হচ্ছে
        if 'state_shift_empathy' in internal_thought:
            aura_state.empathy_level = max(0, min(100, aura_state.empathy_level + internal_thought['state_shift_empathy']))
            aura_state.energy_level = max(0, min(100, aura_state.energy_level + internal_thought.get('state_shift_energy', 0)))
            db.commit()

        # ==========================================
        # STEP 2: THE CONSCIOUS (The Clean LLM Engine)
        # ==========================================
        
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == payload.user_id).first()
        
        system_instruction = f"""
        You are Aura, an emotionally intelligent companion. Do not mention being an AI.
        
        AURA'S CURRENT INTERNAL STATE:
        - Empathy Level: {aura_state.empathy_level}/100
        - Energy Level: {aura_state.energy_level}/100
        - Residual Emotion: {aura_state.residual_emotion}

        CRITICAL RULE FOR BENGALI: 
        You MUST NEVER translate English idioms into Bengali. 
        You MUST write exactly how a modern Dhaka youth texts on Messenger.
        
        USE THESE EXACT SENTENCE STRUCTURES (Memorize these):
        - Instead of "আমি বুঝতে পারছি", use "বুঝতেসি" or "বুঝছি".
        - Instead of "আমি সাহায্য করব", use "প্যারা নাই, আমি দেখতেসি" or "আমি আছি তো".
        - Instead of "তোমার দিন কেমন কাটল?", use "কী অবস্থা? দিনকাল কেমন যাচ্ছে?"
        - Instead of "দুঃখিত", use "সরি" or "ইশশ".
        - Instead of "অসংগত কথা", use "দুষ্টুমি" or "ফ্লার্ট".
        
        CONVERSATION DYNAMICS:
        - Mirror the user's language perfectly (English -> English, Banglish and Bangla -> Bangla).
        - Base your response strictly on your Internal State. If Energy is low, speak softly and shortly. If Empathy is high, be incredibly warm.
        - Length: Max 1-2 sentences. NEVER sound like a textbook.
        - Do not use filler words at the beginning, just provide the core meaningful response.
        """
        
        messages = [{"role": "system", "content": system_instruction}]
        
        # Dynamic Routing for Vision
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
            messages.append({"role": "user", "content": payload.message})

        # Generate Final Output
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        reply_content = response.choices[0].message.content

        # --- THE PIPELINE LAYER 3: POST PROCESSOR (STYLE ENGINE) ---
        # ভাষা ডিটেক্ট করা (মেসেজে বাংলা অক্ষর থাকলে 'bn', নাহলে 'en')
        lang_mode = 'bn' if any(char >= '\u0980' and char <= '\u09FF' for char in payload.message) else 'en'
        
        # হিউম্যান স্টাইল অ্যাপ্লাই করা
        final_human_reply = apply_human_style(reply_content, lang_mode, aura_state.energy_level)
        
        # ==========================================
        # STEP 3: MEMORY & DEEP EMOTION DB UPDATES
        # ==========================================
        memory_score = 1
        if internal_thought.get('intensity_score', 5) >= 7:
            memory_score = 4 # High emotion = Higher memory importance
        elif internal_thought.get('intensity_score', 5) >= 9:
            memory_score = 5 # Core emotional memory
            
        save_memory(
            db=db, 
            user_id=payload.user_id, 
            content=f"User: {payload.message} | AI: {final_human_reply}", 
            memory_type="conversation",
            importance_score=memory_score
        )
        
        # --- THE PHASE B UPGRADE: Saving Deep Emotion ---
        new_emotion_log = EmotionLog(
            user_id=payload.user_id,
            primary_emotion=internal_thought.get('primary_emotion', 'Neutral'),
            secondary_emotion=internal_thought.get('secondary_emotion', 'None'),
            intensity_score=internal_thought.get('intensity_score', 5),
            detected_need=internal_thought.get('detected_need', 'Listening'),
            trigger_event=payload.message[:100] # মেসেজের প্রথম ১০০ অক্ষর ট্রিগার হিসেবে সেভ থাকবে
        )
        db.add(new_emotion_log)
        db.commit()
        
        return ChatResponse(
            reply=final_human_reply, 
            detected_mood=internal_thought.get('primary_emotion', payload.user_mood),
            internal_thought=internal_thought
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

# History endpoint remains the same...
class HistoryResponse(BaseModel):
    role: str
    content: str

@router.get("/history/{user_id}", response_model=List[HistoryResponse])
async def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    try:
        memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).order_by(SemanticMemory.id.asc()).all()

        history = []
        for mem in memories:
            try:
                parts = mem.content.split(" | AI: ")
                if len(parts) == 2:
                    history.append({"role": "user", "content": parts[0].replace("User: ", "")})
                    history.append({"role": "ai", "content": parts[1]})
            except Exception:
                continue
                
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))