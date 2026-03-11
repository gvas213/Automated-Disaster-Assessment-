from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, maps

app = FastAPI()

# Allow frontend dev servers
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(chat.router, prefix="/api")
app.include_router(maps.router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"ok": True}