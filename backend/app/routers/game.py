import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.room import Room
from app.models.question import Question
from app.models.collection import Collection
from app.core.game_manager import game_manager
from app.core.ws_manager import ws_manager

router = APIRouter(tags=["game"])


async def load_room_questions(room_id: str, db: AsyncSession) -> list[dict]:
    """Load questions from Postgres for a room."""
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.collection)
            .selectinload(Collection.questions)
            .selectinload(Question.options)
        )
    )
    room = result.scalar_one_or_none()
    if not room or not room.collection:
        return []

    questions = []
    for q in room.collection.questions:
        questions.append({
            "id": str(q.id),
            "text": q.text,
            "time_limit": q.time_limit,
            "options": [
                {
                    "id": str(o.id),
                    "text": o.text,
                    "is_correct": o.is_correct,
                }
                for o in q.options
            ],
        })
    return questions


@router.websocket("/ws/host/{room_id}")
async def host_websocket(websocket: WebSocket, room_id: str):
    """
    Host connects here. Messages the host can send:
      {"action": "init"}           — load questions into Redis
      {"action": "next_question"}  — advance to next question
      {"action": "show_results"}   — show results for current question
      {"action": "end_game"}       — end the game
    """
    db = None
    try:
        await ws_manager.connect_host(room_id, websocket)

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "init":
                # load questions from Postgres into Redis
                from app.database import async_session
                async with async_session() as db:
                    questions = await load_room_questions(room_id, db)

                if not questions:
                    await ws_manager.send_to_host(room_id, {
                        "event": "error",
                        "message": "No questions found for this room",
                    })
                    continue

                state = await game_manager.init_room(
                    room_id=room_id,
                    host_id=data.get("host_id", ""),
                    questions=questions,
                )
                players = await game_manager.get_players(room_id)
                await ws_manager.send_to_host(room_id, {
                    "event": "room_initialized",
                    "total_questions": len(questions),
                    "player_count": len(players),
                    "players": players,
                })

            elif action == "next_question":
                question = await game_manager.start_question(room_id)

                if question is None:
                    # no more questions — game over
                    await game_manager.set_room_status(room_id, "finished")
                    leaderboard = await game_manager.get_leaderboard(room_id)
                    await ws_manager.broadcast_to_all(room_id, {
                        "event": "game_over",
                        "leaderboard": leaderboard,
                    })
                else:
                    await game_manager.set_room_status(room_id, "active")
                    # send question to everyone (without correct answer for players)
                    await ws_manager.broadcast_to_all(room_id, {
                        "event": "question_start",
                        "question": question,
                    })

            elif action == "show_results":
                state = await game_manager.get_room_state(room_id)
                current_q = int(state["current_question"])
                results = await game_manager.get_question_results(room_id, current_q)
                leaderboard = await game_manager.get_leaderboard(room_id)

                # get the correct answer to reveal
                questions = json.loads(state["questions"])
                question = questions[current_q]
                correct_id = None
                for opt in question["options"]:
                    if opt["is_correct"]:
                        correct_id = opt["id"]
                        break

                await ws_manager.broadcast_to_all(room_id, {
                    "event": "question_results",
                    "question_index": current_q,
                    "correct_option_id": correct_id,
                    "stats": results,
                    "leaderboard": leaderboard,
                })

            elif action == "end_game":
                await game_manager.set_room_status(room_id, "finished")
                leaderboard = await game_manager.get_leaderboard(room_id)
                await ws_manager.broadcast_to_all(room_id, {
                    "event": "game_over",
                    "leaderboard": leaderboard,
                })

    except WebSocketDisconnect:
        ws_manager.disconnect_host(room_id)
        await ws_manager.broadcast_to_players(room_id, {
            "event": "host_disconnected",
        })


@router.websocket("/ws/play/{room_id}")
async def player_websocket(websocket: WebSocket, room_id: str):
    """
    Player connects here. Messages the player can send:
      {"action": "join", "name": "Alice"}
      {"action": "answer", "option_id": "..."}
    """
    player_id = None

    try:
        await ws_manager.connect_player(room_id, "pending", websocket)

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "join":
                player_name = data.get("name", "Anonymous")
                player_id = await game_manager.add_player(room_id, player_name)

                # re-register with actual player_id
                ws_manager.disconnect_player(room_id, "pending")
                ws_manager.rooms.setdefault(room_id, {})[player_id] = websocket

                players = await game_manager.get_players(room_id)

                # confirm to the player
                await ws_manager.send_to_player(room_id, player_id, {
                    "event": "joined",
                    "player_id": player_id,
                    "player_name": player_name,
                })

                # notify host
                await ws_manager.send_to_host(room_id, {
                    "event": "player_joined",
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_count": len(players),
                    "players": players,
                })

            elif action == "answer":
                if not player_id:
                    await websocket.send_json({"event": "error", "message": "Join first"})
                    continue

                state = await game_manager.get_room_state(room_id)
                current_q = int(state["current_question"])

                result = await game_manager.submit_answer(
                    room_id=room_id,
                    player_id=player_id,
                    question_index=current_q,
                    option_id=data.get("option_id", ""),
                )

                if "error" in result:
                    await ws_manager.send_to_player(room_id, player_id, {
                        "event": "error",
                        "message": result["error"],
                    })
                else:
                    # confirm to the player
                    await ws_manager.send_to_player(room_id, player_id, {
                        "event": "answer_accepted",
                        "is_correct": result["is_correct"],
                        "points": result["points"],
                        "time_spent": result["time_spent"],
                    })

                    # notify host about answer count
                    q_results = await game_manager.get_question_results(room_id, current_q)
                    await ws_manager.send_to_host(room_id, {
                        "event": "answer_received",
                        "player_id": player_id,
                        "answers_count": q_results["total_answers"],
                        "player_count": ws_manager.get_player_count(room_id),
                    })

    except WebSocketDisconnect:
        if player_id:
            ws_manager.disconnect_player(room_id, player_id)
            await game_manager.remove_player(room_id, player_id)
            players = await game_manager.get_players(room_id)
            await ws_manager.send_to_host(room_id, {
                "event": "player_left",
                "player_id": player_id,
                "player_count": len(players),
                "players": players,
            })
        else:
            ws_manager.disconnect_player(room_id, "pending")