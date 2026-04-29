import uuid
from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: str
    name: str
    score: int


class LeaderboardResponse(BaseModel):
    room_id: str
    leaderboard: list[LeaderboardEntry]


class QuestionResultResponse(BaseModel):
    question_index: int
    total_answers: int
    correct_answers: int


class GameSummaryResponse(BaseModel):
    room_id: str
    total_questions: int
    leaderboard: list[LeaderboardEntry]
    question_results: list[QuestionResultResponse]