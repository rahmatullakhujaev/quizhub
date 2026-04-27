from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.models  # ensure all models are registered in SQLAlchemy metadata
from app.routers.auth import router as auth_router
from app.routers.questions import router as questions_router

app = FastAPI(title="QuizHub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(questions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}