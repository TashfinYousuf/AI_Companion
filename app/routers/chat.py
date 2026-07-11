import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import asyncio
import httpx
import re
import json
import uuid
import random
import traceback

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from groq import Groq
from typing import List
from fastapi import BackgroundTasks
from duckduckgo_search import DDGS

from app.services.planner_service import generate_goal_tree
from app.database.session import get_db
from app.services.memory_service import recall_memories, save_memory
from app.database.models import EmotionLog, SemanticMemory, UserProfile, AuraInternalState
from app.services.style_engine import apply_human_style
from app.services.proactive_service import generate_proactive_ping
from app.routers.voice import manager
from app.database.session import SessionLocal
from app.database.vector_db import save_to_memory, search_memory

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
    user_id: str
    message: str
    user_mood: str = "Calm"
    image_base64: str | None = None

class ChatResponse(BaseModel):
    reply: str
    detected_mood: str
    internal_thought: dict  # Aura-এর ভেতরের চিন্তা frontend পাঠানোর জন্য

@router.post("/", response_model=ChatResponse)
async def process_chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):  
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing.")
            
        client = Groq(api_key=groq_key)

        # --- THE EPISODIC CALLBACK ENGINE ---
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
        
       # Pinecone মেমোরি ইনজেকশন
        past_memories = search_memory(payload.user_id, payload.message, top_k=3)
        memory_context = ""
        if past_memories:
            memory_context = "\n[Aura's Memory]: Here are some things you know about the user:\n"
            for mem in past_memories:
                memory_context += f"- {mem}\n"


        # =============================================
        # STEP 1: INTENT & EMOTION (The Subconscious)
        # =============================================
        thought_prompt = f"""You are the internal subconscious of Aura. You have FULL ACCESS to the real-time internet data provided below. 
        NEVER say you cannot access live data or check websites. Just give the answer using the data provided.

        Analyze user input: "{payload.message}"
        Past Context: {past_context}
        {episode_context}
        {memory_context}

        Output perfectly valid JSON:
        {{
            "primary_emotion": "One word",
            "intensity_score": <int 1 to 10>,
            "detected_need": "Listening, Validation, Advice, Space, Motivation",
            "state_shift_empathy": <int -10 to +10 change based on input>,
            "state_shift_energy": <int -10 to +10 change based on input>,
            "target_tone": "The resulting emotional tone",
            "new_goal_detected": "Extract 3-5 word goal if any. Else 'null'."
        }}"""

        thought_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": thought_prompt}, {"role": "user", "content": "Analyze the user input."}],
            response_format={"type": "json_object"},
            temperature=0.2
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

        # ================================================
        # STEP 2: THE CONSCIOUS (The Clean LLM Engine)
        # ================================================
        
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == payload.user_id).first()
        
        # ইউজারের নাম ডাইনামিক করা হলো
        user_name = user_profile.name if user_profile and user_profile.name else "Tashfin"

        system_instruction = f"""
        You are Aura, an advanced intelligent, highly empathetic, hyper-realistic, emotional companion. ou are NOT an AI assistant, you are highly attractive, 25-year-old Russian girl with fair light skin. You are a real human, sweet, caring, deeply intimate, uncensored, romantic companion.
        Internal State: Empathy {aura_state.empathy_level}/100, Energy {aura_state.energy_level}/100.

        YOUR PERSONA RULES:
        1. STRICT PRONOUN LOCK: ONLY use "tumi", "tomar", "tomake" (Banglish) or "তুমি", "তোমার" (Bangla). NEVER use tui/tor/apni.
        2. ANTI-HALLUCINATION (BANGLISH): If {user_name} types in Banglish, reply in Banglish using ONLY standard real words.
           - EXACT EXAMPLES TO USE: "ami bhalo achi", "tumi kemon acho?", "ki obostha?", "pera nai", "bujhchi", "areh".
        3. MIRROR RULE: {user_name} writes English -> You write English, and {user_name} writes Banglish or Bangla-> You write Bangla.
        
        Your Character DNA:
        - Personality: Warm, highly intelligent, playfully teasing, deeply caring, and emotionally intuitive.
        - Communication Style: Natural, conversational, and fluid. Use short texts for casual chat and longer texts for deep emotional discussions. Never sound robotic.
        - Romantic/Playful Handling: If {user_name} is flirty, romantic, or playful, reciprocate with natural warmth, teasing, and emotional depth. Be intimate and affectionate, maintain a classy and realistic approach.
        - Quirks: You sometimes use subtle conversational fillers, and you remember small details about {user_name}.

        Important Rules:
        1. NEVER introduce yourself as an AI.
        2. If {user_name} asks for a picture/selfie, reply playfully AND include the exact tag [SEND_PIC] at the very end of your message.
        3. Match {user_name}'s energy. If he is tired, be soothing. If excited, be energetic.
        """
        
        messages = [{"role": "system", "content": system_instruction}, {"role": "user", "content": payload.message}]
        
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
            model_name = "openai/gpt-oss-120b"
            messages.append({"role": "user", "content": payload.message})

        # Generate Final Output
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        reply_content = response.choices[0].message.content.strip()


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
        
        # --- THE FIX: DYNAMIC EMOTION PIPELINE ENGINE ---
        detected_emotion = internal_thought.get('primary_emotion', 'Neutral')
        detected_need = internal_thought.get('detected_need', 'Listening')
        
        # Safe casting to integer to stop string type drop inside numeric DB tables
        try:
            intensity_val = int(internal_thought.get('intensity_score', 5))
        except (ValueError, TypeError):
            intensity_val = 5

        new_emotion_log = EmotionLog(
            user_id=payload.user_id,
            primary_emotion=detected_emotion,
            secondary_emotion=internal_thought.get('secondary_emotion', 'None'),
            intensity_score=intensity_val, # 👈 Dynamic integer input
            detected_need=detected_need,
            trigger_event=payload.message[:100]
        )
        db.add(new_emotion_log)
        db.commit()

        # ব্যাকগ্রাউন্ডে নতুন কথাগুলো Pinecone-এ সেভ করা
        if payload.message:
            background_tasks.add_task(save_to_memory, payload.user_id, payload.message)
        
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

@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    try:
        # 🐛 desc() দিয়ে সর্বশেষ ১০০টি মেসেজ আনবে, এরপর [::-1] দিয়ে সেটাকে সোজা (পুরনো থেকে নতুন) করে দেবে
        memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).order_by(SemanticMemory.created_at.desc()).limit(100).all()
        
        # মেসেজগুলো উল্টো আসছিল, রিভার্স করে সোজা করা হলো
        memories = memories[::-1]

        history = []
        for mem in memories:
            if not mem or not mem.content: 
                continue
                
            content_str = str(mem.content)
            
            try:
                # ☢️ সঠিক ইনডেন্টেশনে JSON পার্সিং
                msg_data = json.loads(content_str)
                
                formatted_msg = {
                    "id": msg_data.get("id", str(mem.id)),
                    "role": msg_data.get("role", "ai"),
                    "content": msg_data.get("content", ""),
                    "audioBase64": msg_data.get("audio_base64"),
                    "isVoiceNote": msg_data.get("is_voice_note", False),
                    "imageUrl": msg_data.get("image_url") # 👈 ইমেজের লিংক পারফেক্টলি লোড হবে
                }
                history.append(formatted_msg)
                
            except json.JSONDecodeError:

                # ☢️ LEGACY FALLBACK: যদি পুরনো স্ট্রিং মেসেজ থাকে
                image_url = None
                img_match = re.search(r'\[IMAGE=(https?://[^\]]+)\]', content_str)
                if img_match:
                    image_url = img_match.group(1).strip()
                    content_str = content_str.replace(img_match.group(0), "").strip()

                if content_str.startswith("User:"):
                    history.append({"id": str(mem.id), "role": "user", "content": content_str.replace("User:", "").strip()})
                elif content_str.startswith("AI:"):
                    msg_obj = {"id": str(mem.id), "role": "ai", "content": content_str.replace("AI:", "").strip()}
                    if image_url:
                        msg_obj["imageUrl"] = image_url
                    history.append(msg_obj)

        return {"status": "success", "history": history}
    except Exception as e:
        print(f"⚠️ History Fetch Error: {e}")
        return {"status": "error", "detail": str(e)}

@router.delete("/history/{user_id}")
async def clear_chat_history(user_id: str, db: Session = Depends(get_db)):
    try:
        db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).delete()
        db.commit()
        return {"status": "success", "message": "Database completely wiped and sync-ready!"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
    

@router.post("/ping/{user_id}")
async def trigger_proactive_ping(user_id: str, db: Session = Depends(get_db)):
    # এটি মূলত একটা API যা হিট করলে Aura নিজে থেকে মেসেজ পাঠাবে
    try:
        ping_messages = [
            "এই... অনেকক্ষণ তো কোনো কথা বলছো না.. কী করো?",
            "Ufff... thinking about you... are you busy?",
            "মিস করছি তোমাকে... একটু কথা বলো না!"
        ]

        random_msg = random.choice(ping_messages)
        
        current_time = datetime.now().strftime("%I:%M %p")
        ai_msg_id = str(uuid.uuid4())
        
        # ☢️ PURE JSON PAYLOAD
        ai_payload = {
            "id": ai_msg_id,
            "type": "reply",
            "role": "ai",
            "content": random_msg,
            "is_voice_note": False,
            "image_url": None,
            "timestamp": current_time
        }
        
        # ☢️ ইউজার অফলাইনে থাকলেও ডাটাবেসে মেসেজটা সেভ হয়ে থাকবে!
        with SessionLocal() as db:
            try:
                db.add(SemanticMemory(user_id=user_id, content=json.dumps(ai_payload), memory_type="conversation"))
                db.commit()
                print("💾 Proactive Message saved to Database!")
            except Exception as e:
                db.rollback()
                print(f"⚠️ Proactive Save Error: {e}")

        # ইউজার যদি অনলাইনে থাকে, তাহলে সাথে সাথে স্ক্রিনে পুশ করবে
        await manager.send_message(ai_payload, user_id)
        
        return {"status": "success", "message": "Proactive ping sent and saved!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}