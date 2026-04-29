from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth import router as auth_router
from app.routers.questions import router as questions_router
from app.routers.collections import router as collections_router
from app.routers.rooms import router as rooms_router
from app.routers.game import router as game_router
from app.routers.leaderboard import router as leaderboard_router
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(title="QuizHub API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(questions_router)
app.include_router(collections_router)
app.include_router(rooms_router)
app.include_router(game_router)
app.include_router(leaderboard_router)


@app.get("/health")
async def health():
    return {"status": "ok"}