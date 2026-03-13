from fastapi import APIRouter
from models.schemas import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Dummy response for now
    return ChatResponse(
        reply=f"You said: {request.message}"
    )