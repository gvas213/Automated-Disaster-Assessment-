from fastapi import FastAPI
from rag_router import router as rag_router

app = FastAPI()
app.include_router(rag_router, prefix="/api")