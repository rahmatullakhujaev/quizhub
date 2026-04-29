from fastapi import APIRouter, HTTPException
from app.core.game_manager import game_manager
from app.schemas.game import LeaderboardResponse, GameSummaryResponse, QuestionResultResponse

router = APIRouter(prefix="/api/games", tags=["game"])


@router.get("/{room_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(room_id: str):
    """Public endpoint — anyone in the room can fetch the live leaderboard."""
    state = await game_manager.get_room_state(room_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found or expired")

    leaderboard = await game_manager.get_leaderboard(room_id)
    return LeaderboardResponse(room_id=room_id, leaderboard=leaderboard)


@router.get("/{room_id}/results/{question_index}", response_model=QuestionResultResponse)
async def get_question_results(room_id: str, question_index: int):
    """Get results for a specific question."""
    state = await game_manager.get_room_state(room_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found or expired")

    total_q = int(state["total_questions"])
    if question_index < 0 or question_index >= total_q:
        raise HTTPException(status_code=400, detail="Invalid question index")

    results = await game_manager.get_question_results(room_id, question_index)
    return QuestionResultResponse(question_index=question_index, **results)


@router.get("/{room_id}/summary", response_model=GameSummaryResponse)
async def get_game_summary(room_id: str):
    """Full game summary — leaderboard + all question results. Best called after game ends."""
    state = await game_manager.get_room_state(room_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found or expired")

    total_q = int(state["total_questions"])
    leaderboard = await game_manager.get_leaderboard(room_id)

    question_results = []
    for i in range(total_q):
        results = await game_manager.get_question_results(room_id, i)
        question_results.append(
            QuestionResultResponse(question_index=i, **results)
        )

    return GameSummaryResponse(
        room_id=room_id,
        total_questions=total_q,
        leaderboard=leaderboard,
        question_results=question_results,
    )