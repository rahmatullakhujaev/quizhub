import asyncio
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import async_session
from app.core.redis import get_redis
from app.models.game_session import GameSession
from app.models.room import Room, RoomStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("game_saver")

SCAN_INTERVAL = 60  
BATCH_PREFIX = "room:"


async def find_finished_games() -> list[str]:
    """Scan Redis for rooms with status 'finished'."""
    r = await get_redis()
    room_ids = []

    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor, match="room:*:state", count=100)
        for key in keys:
            status = await r.hget(key, "status")
            if status == "finished":
                room_id = key.split(":")[1]
                room_ids.append(room_id)
        if cursor == 0:
            break

    return room_ids


async def save_game_to_postgres(room_id: str) -> bool:
    """Save a finished game from Redis to Postgres."""
    r = await get_redis()

    # check if already saved
    async with async_session() as db:
        existing = await db.execute(
            select(GameSession).where(GameSession.room_id == room_id)
        )
        if existing.scalar_one_or_none():
            logger.info(f"[{room_id}] Already saved, skipping")
            return False

    state_key = f"room:{room_id}:state"
    state = await r.hgetall(state_key)

    if not state:
        logger.warning(f"[{room_id}] No state found in Redis")
        return False

    total_questions = int(state.get("total_questions", 0))

    async with async_session() as db:
        result = await db.execute(
            select(Room).where(Room.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            logger.warning(f"[{room_id}] Room not found in Postgres")
            return False
        host_id = str(room.host_id)

    # get leaderboard
    leaderboard_key = f"room:{room_id}:leaderboard"
    scores = await r.zrevrange(leaderboard_key, 0, -1, withscores=True)

    players_key = f"room:{room_id}:players"
    players_raw = await r.hgetall(players_key)

    leaderboard = []
    for rank, (player_id, score) in enumerate(scores, 1):
        player_data = json.loads(players_raw.get(player_id, "{}"))
        leaderboard.append({
            "rank": rank,
            "player_id": player_id,
            "name": player_data.get("name", "Unknown"),
            "score": int(score),
        })

    # get question results
    question_results = []
    for i in range(total_questions):
        answers_key = f"room:{room_id}:answers:{i}"
        answers_raw = await r.hgetall(answers_key)
        total_answers = len(answers_raw)
        correct_answers = sum(
            1 for data in answers_raw.values()
            if json.loads(data).get("is_correct", False)
        )
        question_results.append({
            "question_index": i,
            "total_answers": total_answers,
            "correct_answers": correct_answers,
        })

    # build results JSON
    results = {
        "leaderboard": leaderboard,
        "question_results": question_results,
    }

    # save to Postgres
    async with async_session() as db:
        game_session = GameSession(
            room_id=room_id,
            host_id=host_id,
            total_questions=total_questions,
            player_count=len(players_raw),
            results_json=results,
        )
        db.add(game_session)

        # update room status in Postgres too
        result = await db.execute(
            select(Room).where(Room.id == room_id)
        )
        room = result.scalar_one_or_none()
        if room and room.status != RoomStatus.FINISHED:
            room.status = RoomStatus.FINISHED

        await db.commit()
        logger.info(f"[{room_id}] Saved: {len(leaderboard)} players, {total_questions} questions")

    return True


async def cleanup_redis(room_id: str):
    """Remove all Redis keys for a finished game after saving."""
    r = await get_redis()
    state = await r.hgetall(f"room:{room_id}:state")
    total_q = int(state.get("total_questions", 0))

    keys = [
        f"room:{room_id}:state",
        f"room:{room_id}:players",
        f"room:{room_id}:leaderboard",
    ]
    for i in range(total_q):
        keys.append(f"room:{room_id}:question:{i}")
        keys.append(f"room:{room_id}:answers:{i}")

    deleted = await r.delete(*keys)
    logger.info(f"[{room_id}] Cleaned up {deleted} Redis keys")


async def run_batch():
    """Main batch loop — runs every SCAN_INTERVAL seconds."""
    logger.info(f"Game saver worker started (interval: {SCAN_INTERVAL}s)")

    while True:
        try:
            finished_games = await find_finished_games()

            if finished_games:
                logger.info(f"Found {len(finished_games)} finished game(s)")

                for room_id in finished_games:
                    try:
                        saved = await save_game_to_postgres(room_id)
                        if saved:
                            await cleanup_redis(room_id)
                    except Exception as e:
                        logger.error(f"[{room_id}] Error processing: {e}")
            else:
                logger.debug("No finished games found")

        except Exception as e:
            logger.error(f"Batch scan error: {e}")

        await asyncio.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_batch())