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

