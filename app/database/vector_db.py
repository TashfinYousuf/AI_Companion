import os
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# ১. Pinecone কানেকশন সেটআপ
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "aura-memory"
index = pc.Index(index_name)

# ২. The Latest Gemini Embedding Model (Outputs 3072 dimensions)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

def save_to_memory(user_id: str, text: str):
    """ইউজারের কথা ব্রেইনে (Pinecone) সেভ করার ফাংশন"""
    try:
        vector = embeddings.embed_query(text)
        index.upsert(
            vectors=[
                {"id": f"{user_id}_{hash(text)}", "values": vector, "metadata": {"user_id": user_id, "text": text}}
            ]
        )
        return True
    except Exception as e:
        print(f"Memory Save Error: {e}")
        return False

def search_memory(user_id: str, query: str, top_k: int = 3):
    """পুরনো স্মৃতি খোঁজার ফাংশন"""
    try:
        query_vector = embeddings.embed_query(query)
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": {"$eq": user_id}} 
        )
        
        memories = [match['metadata']['text'] for match in results['matches']]
        return memories
    except Exception as e:
        print(f"Memory Search Error: {e}")
        return []