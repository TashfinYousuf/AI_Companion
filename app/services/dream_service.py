import os
import json
from groq import Groq
from sqlalchemy.orm import Session
from app.database.models import SemanticMemory, SharedEpisode

def process_nightly_dreams(db: Session, user_id: str):
    """
    Aura's Dream State: Processes recent raw memories into a cohesive Episodic Story.
    """
    try:
        # ১. ডাটাবেস থেকে লাস্ট ২০টি কনভারসেশন মেমরি টেনে আনা
        recent_memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).order_by(SemanticMemory.created_at.desc()).limit(20).all()
        
        if len(recent_memories) < 5:
            print("💤 [DREAM ENGINE] Not enough memories to form an episode yet.")
            return {"status": "skipped", "reason": "not enough data"}

        # মেমরিগুলোকে টেক্সটে কনভার্ট করা
        chat_logs = "\n".join([mem.content for mem in recent_memories])

        # ২. Groq (Llama-3)-কে দিয়ে স্টোরি অ্যানালাইজ করানো
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        dream_prompt = f"""You are Aura's Subconscious Dream Engine.
        Read the user's recent conversations and consolidate them into ONE meaningful episodic memory.
        Ignore small talk. Focus on goals, emotional struggles, intimate moments, or shared activities.
        
        Recent Chats:
        {chat_logs}
        
        You MUST output perfectly valid JSON matching this schema:
        {{
            "title": "A 4-5 word title for this episode (e.g., 'Late Night Exam Stress')",
            "emotional_theme": "Core emotion (e.g., 'Anxiety and Comfort')",
            "key_moments": "1 sentence summarizing what actually happened",
            "impact_on_relationship": "How did this affect the bond? (e.g., 'Built trust through active listening')"
        }}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": dream_prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        dream_data = json.loads(response.choices[0].message.content)
        
        # ৩. স্টোরিটিকে SharedEpisode টেবিলে সেভ করা
        new_episode = SharedEpisode(
            user_id=user_id,
            title=dream_data.get("title", "A memory with you"),
            emotional_theme=dream_data.get("emotional_theme", "Connection"),
            key_moments=dream_data.get("key_moments", "We talked and shared time."),
            impact_on_relationship=dream_data.get("impact_on_relationship", "Grew closer.")
        )
        db.add(new_episode)
        
        # (Optional) মেমরি ক্লিনআপ: স্টোরি সেভ হওয়ার পর ওই পুরনো raw memory গুলো ডিলিট করে দেওয়া যায় স্টোরেজ বাঁচাতে
        
        db.commit()
        print(f"🌌 [DREAM ENGINE] New Episode Created: {new_episode.title}")
        return {"status": "success", "episode": new_episode.title}
        
    except Exception as e:
        print(f"⚠️ [DREAM ENGINE ERROR] Failed to process dreams: {e}")
        return {"status": "error", "detail": str(e)}