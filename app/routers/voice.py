import os
import tempfile
import edge_tts
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

router = APIRouter(prefix="/api/voice", tags=["Voice Engine"])

class TTSRequest(BaseModel):
    text: str

# বাংলা ফন্ট ডিটেক্ট করার ম্যাজিক ফাংশন
def contains_bengali(text: str) -> bool:
    return bool(re.search(r'[\u0980-\u09FF]', text))

@router.post("/tts")
async def process_tts(payload: TTSRequest):
    try:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        # বাংলা থাকলে 'নবনীতা', ইংরেজি থাকলে 'আরিয়া' (High Quality Human-like Voices)
        voice_model = "bn-BD-NabanitaNeural" if contains_bengali(payload.text) else "en-US-AriaNeural"
        
        communicate = edge_tts.Communicate(payload.text, voice_model)
        await communicate.save(path)
        
        return FileResponse(
            path, 
            media_type="audio/mpeg", 
            background=BackgroundTask(os.remove, path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))