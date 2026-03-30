from fastapi import FastAPI
from rag_router import router as rag_router
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.include_router(rag_router, prefix="/api")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))

@app.get("/debug")
async def debug():
    import openai
    # use a real embedding to query
    response = openai.embeddings.create(
        input="building damage hurricane harvey",
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding
    
    results = index.query(
        vector=embedding,
        top_k=5,
        include_metadata=True
    )
    return {"samples": [r["metadata"]["text"] for r in results["matches"]]}