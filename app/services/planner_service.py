import os
import json
from groq import Groq
from app.database.session import SessionLocal
from app.database.models import Goal, SubTask

def generate_goal_tree(user_id: str, goal_title: str):
    # ব্যাকগ্রাউন্ড টাস্কের জন্য ফ্রেশ ডাটাবেস কানেকশন
    db = SessionLocal()
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        system_prompt = f"""You are Aura's Autonomous Planning Agent. 
        The user has established a new long-term goal: "{goal_title}".
        Break this down into 3 or 4 highly practical, actionable sub-tasks.
        
        You MUST output perfectly valid JSON matching this schema:
        {{
            "description": "1 sentence summarizing the goal strategy",
            "tasks": ["Task 1", "Task 2", "Task 3"]
        }}"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Create goal tree for: {goal_title}"}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        plan = json.loads(response.choices[0].message.content)
        
        new_goal = Goal(
            user_id=user_id,
            title=goal_title,
            description=plan.get("description", "")
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        
        for task_title in plan.get("tasks", []):
            new_task = SubTask(goal_id=new_goal.id, title=task_title)
            db.add(new_task)
            
        db.commit()
        print(f"🎯 [AGENT] Goal Tree Created: {goal_title}")
        
    except Exception as e:
        print(f"⚠️ [AGENT ERROR] Failed to create goal tree: {e}")
    finally:
        db.close() # কানেকশন সেফলি ক্লোজ করা