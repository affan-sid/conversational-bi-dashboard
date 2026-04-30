from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.services.chat_service import handle_chat

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/chat")
def chat(request: ChatRequest):
    return handle_chat(request.question)