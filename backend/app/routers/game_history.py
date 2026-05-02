import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.game_session import GameSession
from app.core.deps import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/history", tags=["history"])


class GameHistoryResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    host_id: uuid.UUID
    total_questions: int
    player_count: int
    results_json: dict
    played_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[GameHistoryResponse])
async def list_game_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all past games hosted by the current user."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.host_id == current_user.id)
        .order_by(GameSession.played_at.desc())
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=GameHistoryResponse)
async def get_game_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific past game."""
    result = await db.execute(
        select(GameSession).where(
            GameSession.id == session_id,
            GameSession.host_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    return session