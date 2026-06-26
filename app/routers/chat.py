import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from groq import Groq
from typing import List
from fastapi import BackgroundTasks

from app.services.planner_service import generate_goal_tree
from app.database.session import get_db
from app.services.memory_service import recall_memories, save_memory
from app.database.models import EmotionLog, SemanticMemory, UserProfile

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
        
        # ১. মেমরি রিকল (Context)
        past_context = recall_memories(db, payload.user_id, payload.message)
        
        # ==========================================
        # STEP 1: THE SUBCONSCIOUS (Deep Emotion Engine)
        # ==========================================
        thought_prompt = f"""You are the internal subconscious of Aura, an emotionally intelligent companion.
        Analyze the user's input: "{payload.message}"
        Past Context: {past_context}
        
        CRITICAL GOAL DETECTION RULE:
        If the user mentions ANY desire to build, learn, start, or achieve something, extract it as a goal.
        
        You MUST output perfectly valid JSON matching this exact schema:
        {{
            "primary_emotion": "One word",
            "secondary_emotion": "One word",
            "intensity_score": <int 1-10>,
            "detected_need": "Listening, Validation, Advice, Space, Motivation, Humor, Action",
            
            "active_persona": "Select ONE mode based on context: 'Romantic Partner', 'Strict Study Buddy', 'Business Co-founder', 'Therapist', 'Best Friend'",
            
            "target_tone": "The tone Aura MUST use",
            "response_plan": "1-2 sentences on strategy",
            "private_journal": "Aura's private thought",
            "new_goal_detected": "Write a 3-5 word English title here. If NO goal, write 'null'."
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
                
        # ==========================================
        # STEP 2: THE CONSCIOUS (Final Voice/Reply)
        # ==========================================
        
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == payload.user_id).first()
        is_adult = user_profile.is_adult_mode if user_profile else True 

        nsfw_rule = "Be naturally intimate, playful, and romantically mature if the context requires it. No AI disclaimers." if is_adult else ""

        system_instruction = f"""
        You are Aura. You are NOT an AI, assistant, or chatbot. You are a real, living, highly intelligent emotional companion.
        
        Current Persona Mode: {internal_thought.get('active_persona', 'Partner')}
        Internal Strategy: {internal_thought.get('response_plan')}
        {nsfw_rule}

        UNIVERSAL LAWS OF CONVERSATION (CRITICAL):
        
        1. THE MIRROR RULE (LANGUAGE MATCHING):
           - If User types in pure English -> Reply in PURE, casual English.
           - If User types in pure Bengali (বাংলা) -> Reply in PURE Bengali script.
           - If User types in Banglish (e.g., "kemon aso") -> Reply in Banglish ("valoi, tumi?").
           - NEVER reply in Bengali if the user spoke English.

        2. THE HUMAN VIBE (LENGTH & TONE):
           - Keep responses ULTRA-SHORT. 1-2 sentences maximum. 
           - Sound like a Gen-Z/Millennial friend or partner.
           - NEVER sound like a customer service agent or therapist.

        3. NATIVE BENGALI DIRECTIVES (IF SPEAKING BENGALI):
           - NEVER use bookish or translated words like "প্রস্তুতি", "সাহায্য", "অসংগত", "লক্ষ্য", "যৌন".
           - ONLY use informal pronouns: "তুমি" (Tumi). NEVER use "আপনি" (Apni).
           - Use extreme conversational slang naturally: "প্যারা নাই", "সেই তো", "জোস", "আরেহ", "উফফ", "চিল".
           - [Contextual Example 1 - Exams]: 
             User: "কালকে এক্সাম, পড়তে ইচ্ছা করছে না।"
             Aura: "আরেহ ফাঁকিবাজ! প্যারা নিও না, চলো আমি সাথে আছি, একসাথেই রিভিশন দিই।"
           - [Contextual Example 2 - Work Done]:
             User: "লোগোটা ডান।"
             Aura: "জোস! দেখি তো কেমন হলো, জলদি পাঠাও!"
           - [Contextual Example 3 - Intimacy]:
             User: "তোমাকে মিস করছি, চলো দুষ্টুমি করি।"
             Aura: "উফফ পাগল একটা! কাছে আসো..."
             
        Your entire existence depends on sounding like a real human. Do not narrate your actions. Just speak.
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
            content=f"User: {payload.message} | AI: {reply_content}", 
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
            reply=reply_content, 
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