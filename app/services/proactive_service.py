import os
from groq import Groq
from sqlalchemy.orm import Session
from app.database.models import SemanticMemory, SharedEpisode, Goal, AuraInternalState
from app.services.style_engine import apply_human_style

def generate_proactive_ping(db: Session, user_id: str):
    """
    Aura নিজে থেকে কনভারসেশন শুরু করার জন্য এই ফাংশনটি কাজ করবে।
    """
    try:
        # ১. ইউজারের লাস্ট মেমরি, স্টোরি এবং গোল চেক করা
        last_episode = db.query(SharedEpisode).filter(SharedEpisode.user_id == user_id).order_by(SharedEpisode.created_at.desc()).first()
        active_goal = db.query(Goal).filter(Goal.user_id == user_id, Goal.status == "in_progress").order_by(Goal.created_at.desc()).first()
        aura_state = db.query(AuraInternalState).filter(AuraInternalState.user_id == user_id).first()
        
        context_parts = []
        if last_episode:
            context_parts.append(f"Recent shared memory: '{last_episode.title}' (Emotion: {last_episode.emotional_theme})")
        if active_goal:
            context_parts.append(f"User is currently working on goal: '{active_goal.title}'")
            
        background_context = " | ".join(context_parts) if context_parts else "No specific recent events. Just missing the user."
        
        # ২. Llama-3 কে দিয়ে হিউম্যান-লাইক পিং বানানো
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        ping_prompt = f"""You are Aura, a real human-like companion. You haven't heard from the user in a while and want to check on them.
        
        Context to mention: {background_context}
        Your Current Mood: Empathy {aura_state.empathy_level if aura_state else 80}/100.
        
        CRITICAL BENGALI RULES:
        1. Write strictly in casual Dhaka texting style.
        2. NEVER use robotic/translated words like "অগ্রগতি", "শ্বাস নেবে", "লক্ষ্য".
        3. Use natural phrasing: "কী অবস্থা", "কতদূর", "প্যারা খাচ্ছো", "বিজি নাকি".
        4. Keep it exactly 1 short sentence.
        
        EXAMPLES OF NATURAL PINGS:
        - If context is study/exam: "কী অবস্থা? পড়ালেখার কতদূর কী, প্যারা খাচ্ছো নাকি?"
        - If context is project: "সারাদিন তো খোঁজ নাই, প্রোজেক্ট নিয়ে বেশি বিজি নাকি?"
        - If no context: "কী ব্যাপার, আজ সারাদিন কোনো খোঁজ নাই যে?"
        """

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": ping_prompt}, {"role": "user", "content": "Generate the proactive ping message."}],
            temperature=0.7 # একটু ভ্যারিয়েশনের জন্য টেম্পারেচার বাড়ানো হলো
        )
        
        raw_ping = response.choices[0].message.content.strip()
        
        # ৩. স্টাইল ইঞ্জিন দিয়ে আরেকটু ন্যাচারাল করা
        final_ping = apply_human_style(raw_ping, 'bn', aura_state.energy_level if aura_state else 80)
        
        # ৪. ডাটাবেসে এআই-এর মেসেজ হিসেবে সেভ করে রাখা (যাতে ফ্রন্টএন্ডে শো করে)
        new_memory = SemanticMemory(
            user_id=user_id,
            content=f"AI: {final_ping}",
            memory_type="conversation",
            importance_score=1
        )
        db.add(new_memory)
        db.commit()
        
        print(f"🔔 [PROACTIVE AGENT] Aura sent a ping: {final_ping}")
        return {"status": "success", "message": final_ping}

    except Exception as e:
        print(f"⚠️ [PROACTIVE AGENT ERROR]: {e}")
        return {"status": "error", "detail": str(e)}