import os
import openai
from pinecone import Pinecone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))

router = APIRouter()

#models for request and response 
class ChatRequest(BaseModel):
    message: str    #user query
    chat_history: list[dict] = []   #prev msgs 

class ChatResponse(BaseModel):
    answer: str #llm response
    sources: list[str]  #pdfs used to answer

#convert string to vector (same as what is used in ingest.py)
def embed(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

#search pinecone/DB for most relevant chunk(s)
#using cosine similarity (gives top_k similar chunks)
def retrieve_context(query, top_k=4):
    query_embedding = embed(query)
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True   #used for text and source (for testing can be removed later)
    )
    chunks = [r["metadata"]["text"] for r in results["matches"]]    #extract text from chunk
    sources = list(set([r["metadata"]["source"] for r in results["matches"]]))  #extract source file
    return chunks, sources

#prompt - needs adjustment to use RAG as tool
SYSTEM_PROMPT = """You are a helpful assistant answering questions about Hurricane Harvey 
and its impact. Use only the provided context to answer. If the answer isn't in the context, 
say you don't have enough information on that topic. Be factual and concise."""

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        chunks, sources = retrieve_context(request.message)
        context = "\n\n".join(chunks)

        #build msg - system prompt, history, query
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += request.chat_history    #prior convo/queries
        #lump in context to request
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {request.message}"
        })

        #call to LLM
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )
        
        #response 
        return ChatResponse(
            answer=response.choices[0].message.content,
            sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))