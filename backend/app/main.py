import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.routers.auth import router as auth_router
from app.routers.questions import router as questions_router
from app.routers.collections import router as collections_router
from app.routers.rooms import router as rooms_router
from app.routers.game import router as game_router
from app.routers.leaderboard import router as leaderboard_router
from app.routers.game_history import router as game_history_router
from app.core.redis import close_redis, get_redis
from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION
from app.rate_limiter import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(title="QuizHub API", version="1.0.0", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, redis_getter=get_redis)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(auth_router)
app.include_router(questions_router)
app.include_router(collections_router)
app.include_router(rooms_router)
app.include_router(game_router)
app.include_router(leaderboard_router)
app.include_router(game_history_router)


@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    path = request.url.path
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method, path=path, status=response.status_code
    ).inc()
    HTTP_REQUEST_DURATION.labels(method=request.method, path=path).observe(duration)
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}