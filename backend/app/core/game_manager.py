import json
import time
import uuid
from app.core.redis import get_redis


class GameManager:

    # ── Key builders ──

    @staticmethod
    def _room_key(room_id: str) -> str:
        return f"room:{room_id}:state"

    @staticmethod
    def _players_key(room_id: str) -> str:
        return f"room:{room_id}:players"

    @staticmethod
    def _question_key(room_id: str, question_index: int) -> str:
        return f"room:{room_id}:question:{question_index}"

    @staticmethod
    def _answers_key(room_id: str, question_index: int) -> str:
        return f"room:{room_id}:answers:{question_index}"

    @staticmethod
    def _leaderboard_key(room_id: str) -> str:
        return f"room:{room_id}:leaderboard"

    # ── Room state ──

    async def init_room(self, room_id: str, host_id: str, questions: list[dict]) -> dict:
        """Initialize a room in Redis with questions and state."""
        r = await get_redis()
        state = {
            "room_id": room_id,
            "host_id": host_id,
            "status": "waiting",
            "current_question": -1,
            "total_questions": len(questions),
            "questions": json.dumps(questions),
        }
        await r.hset(self._room_key(room_id), mapping=state)
        await r.expire(self._room_key(room_id), 3600)  # 1 hour TTL
        return state

    async def get_room_state(self, room_id: str) -> dict | None:
        r = await get_redis()
        state = await r.hgetall(self._room_key(room_id))
        return state if state else None

    async def set_room_status(self, room_id: str, status: str):
        r = await get_redis()
        await r.hset(self._room_key(room_id), "status", status)

    # ── Players ──

    async def add_player(self, room_id: str, player_name: str) -> str:
        """Add a player, return their player_id."""
        r = await get_redis()
        player_id = str(uuid.uuid4())
        player_data = json.dumps({
            "id": player_id,
            "name": player_name,
            "score": 0,
        })
        await r.hset(self._players_key(room_id), player_id, player_data)
        await r.expire(self._players_key(room_id), 3600)
        # initialize leaderboard score
        await r.zadd(self._leaderboard_key(room_id), {player_id: 0})
        await r.expire(self._leaderboard_key(room_id), 3600)
        return player_id

    async def get_players(self, room_id: str) -> list[dict]:
        r = await get_redis()
        players_raw = await r.hgetall(self._players_key(room_id))
        players = []
        for pid, data in players_raw.items():
            p = json.loads(data)
            players.append(p)
        return players

    async def remove_player(self, room_id: str, player_id: str):
        r = await get_redis()
        await r.hdel(self._players_key(room_id), player_id)
        await r.zrem(self._leaderboard_key(room_id), player_id)

    # ── Questions ──

    async def start_question(self, room_id: str) -> dict | None:
        """Advance to next question. Returns question data or None if game over."""
        r = await get_redis()
        current = int(await r.hget(self._room_key(room_id), "current_question"))
        total = int(await r.hget(self._room_key(room_id), "total_questions"))
        next_q = current + 1

        if next_q >= total:
            return None

        await r.hset(self._room_key(room_id), "current_question", next_q)

        questions = json.loads(await r.hget(self._room_key(room_id), "questions"))
        question = questions[next_q]

        # store question start time
        await r.hset(
            self._question_key(room_id, next_q),
            mapping={
                "started_at": str(time.time()),
                "time_limit": str(question["time_limit"]),
            },
        )
        await r.expire(self._question_key(room_id, next_q), 3600)

        return {
            "question_index": next_q,
            "total_questions": total,
            "text": question["text"],
            "time_limit": question["time_limit"],
            "options": [
                {"id": opt["id"], "text": opt["text"]}
                for opt in question["options"]
            ],
        }

    # ── Answers + Scoring ──

    async def submit_answer(
        self, room_id: str, player_id: str, question_index: int, option_id: str
    ) -> dict:
        """Record an answer and calculate score."""
        r = await get_redis()

        # check question answered
        existing = await r.hexists(self._answers_key(room_id, question_index), player_id)
        if existing:
            return {"error": "Already answered"}

        # get question timing
        q_data = await r.hgetall(self._question_key(room_id, question_index))
        started_at = float(q_data["started_at"])
        time_limit = int(q_data["time_limit"])

        time_spent = time.time() - started_at

        # get correct answer
        questions = json.loads(await r.hget(self._room_key(room_id), "questions"))
        question = questions[question_index]

        correct_option_id = None
        for opt in question["options"]:
            if opt["is_correct"]:
                correct_option_id = opt["id"]
                break

        is_correct = option_id == correct_option_id

        # calculate score: ((time_limit - time_spent) / time_limit) * 500 + 500
        if is_correct:
            capped_time = min(max(time_spent, 0), time_limit)
            points = int(((time_limit - capped_time) / time_limit) * 500 + 500)
        else:
            points = 0

        # save answer
        answer_data = json.dumps({
            "option_id": option_id,
            "is_correct": is_correct,
            "time_spent": round(time_spent, 2),
            "points": points,
        })
        await r.hset(self._answers_key(room_id, question_index), player_id, answer_data)
        await r.expire(self._answers_key(room_id, question_index), 3600)

        # update leaderboard
        if points > 0:
            await r.zincrby(self._leaderboard_key(room_id), points, player_id)

        # update player total score
        player_data = json.loads(await r.hget(self._players_key(room_id), player_id))
        player_data["score"] += points
        await r.hset(self._players_key(room_id), player_id, json.dumps(player_data))

        return {
            "is_correct": is_correct,
            "points": points,
            "time_spent": round(time_spent, 2),
        }

    async def get_question_results(self, room_id: str, question_index: int) -> dict:
        """Get answer stats for a question."""
        r = await get_redis()
        answers_raw = await r.hgetall(self._answers_key(room_id, question_index))
        total = len(answers_raw)
        correct = 0
        for data in answers_raw.values():
            a = json.loads(data)
            if a["is_correct"]:
                correct += 1
        return {"total_answers": total, "correct_answers": correct}

    # ── Leaderboard ──

    async def get_leaderboard(self, room_id: str) -> list[dict]:
        """Get leaderboard sorted by score descending."""
        r = await get_redis()
        scores = await r.zrevrange(self._leaderboard_key(room_id), 0, -1, withscores=True)
        players = await r.hgetall(self._players_key(room_id))

        leaderboard = []
        for rank, (player_id, score) in enumerate(scores, 1):
            player_data = json.loads(players.get(player_id, "{}"))
            leaderboard.append({
                "rank": rank,
                "player_id": player_id,
                "name": player_data.get("name", "Unknown"),
                "score": int(score),
            })
        return leaderboard

    # ── Cleanup ──

    async def cleanup_room(self, room_id: str):
        """Delete all Redis keys for a room."""
        r = await get_redis()
        state = await self.get_room_state(room_id)
        if state:
            total = int(state.get("total_questions", 0))
            keys = [
                self._room_key(room_id),
                self._players_key(room_id),
                self._leaderboard_key(room_id),
            ]
            for i in range(total):
                keys.append(self._question_key(room_id, i))
                keys.append(self._answers_key(room_id, i))
            await r.delete(*keys)


game_manager = GameManager()