import os
from fastembed import TextEmbedding
from sqlalchemy.orm import Session
from app.database.models import SemanticMemory
from dotenv import load_dotenv

load_dotenv()
ENV = os.getenv("ENV", "development")

# FastEmbed ইনিশিয়ালাইজেশন (PyTorch ছাড়াই সুপার ফাস্ট ONNX রানটাইমে চলবে)
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_embedding(text: str) -> list[float]:
    # FastEmbed লিস্ট ইনপুট নেয় এবং জেনারেটর রিটার্ন করে
    embeddings = list(embedding_model.embed([text]))
    return embeddings[0].tolist()

def save_memory(db: Session, user_id: str, content: str, memory_type: str = "general", importance_score: int = 1):
    vector = get_embedding(content)
    new_memory = SemanticMemory(
        user_id=user_id,
        memory_type=memory_type,
        content=content,
        embedding=vector,
        importance_score=importance_score
    )
    db.add(new_memory)
    db.commit()

def recall_memories(db: Session, user_id: str, current_message: str, limit: int = 3) -> str:
    query_vector = get_embedding(current_message)
    
    if ENV == "production":
        similar_memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id
        ).order_by(
            SemanticMemory.embedding.l2_distance(query_vector)
        ).limit(limit).all()
    else:
        all_memories = db.query(SemanticMemory).filter(SemanticMemory.user_id == user_id).all()
        
        def l2_distance(vec1, vec2):
            return sum((a - b) ** 2 for a, b in zip(vec1, vec2))
        
        similar_memories = sorted(
            all_memories, 
            key=lambda m: l2_distance(m.embedding, query_vector)
        )[:limit]
    
    if not similar_memories:
        return ""
    
    context = "\n".join([f"- {mem.content}" for mem in similar_memories])
    return f"Relevant Past Memories:\n{context}"