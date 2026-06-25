import os
from openai import OpenAI
from fastapi import UploadFile

def transcribe_audio(audio_file: UploadFile) -> str:
    """অডিও ফাইল রিসিভ করে টেক্সটে কনভার্ট করবে"""
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    # অডিও ফাইলটি সাময়িকভাবে সেভ করার জন্য
    temp_file_path = f"temp_{audio_file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(audio_file.file.read())
            
        with open(temp_file_path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio
            )
        return transcript.text
    
    finally:
        # কাজ শেষ হলে টেম্পোরারি ফাইলটি ডিলিট করে দেওয়া (স্টোরেজ বাঁচানোর জন্য)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)