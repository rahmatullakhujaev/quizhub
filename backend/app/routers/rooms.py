import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.collection import Collection
from app.models.room import Room, RoomStatus
from app.core.deps import get_current_user
from app.core.room_code_generator import generate_room_code
from app.schemas.room import RoomCreate, RoomResponse, RoomDetailResponse, RoomJoinResponse

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # option 1: use existing collection
    if body.collection_id:
        result = await db.execute(
            select(Collection).where(
                Collection.id == body.collection_id,
                Collection.creator_id == current_user.id,
            )
        )
        collection = result.scalar_one_or_none()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        collection_id = collection.id

    # option 2: pick individual questions + optionally save as new collection
    elif body.question_ids:
        result = await db.execute(
            select(Question).where(
                Question.id.in_(body.question_ids),
                Question.creator_id == current_user.id,
            )
        )
        questions = result.scalars().all()
        if len(questions) != len(body.question_ids):
            raise HTTPException(status_code=400, detail="Some questions not found or don't belong to you")

        if body.save_as_collection:
            new_collection = Collection(
                title=body.collection_title or "Untitled Collection",
                creator_id=current_user.id,
            )
            new_collection.questions = list(questions)
            db.add(new_collection)
            await db.flush()
            collection_id = new_collection.id
        else:
            # create a temporary collection for this room
            temp_collection = Collection(
                title=f"Room questions",
                creator_id=current_user.id,
            )
            temp_collection.questions = list(questions)
            db.add(temp_collection)
            await db.flush()
            collection_id = temp_collection.id
    else:
        raise HTTPException(status_code=400, detail="Provide collection_id or question_ids")

    # generate unique room code
    for _ in range(10):
        code = generate_room_code()
        exists = await db.execute(select(Room).where(Room.room_code == code))
        if not exists.scalar_one_or_none():
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique room code")

    room = Room(
        room_code=code,
        host_id=current_user.id,
        collection_id=collection_id,
        status=RoomStatus.WAITING,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get("/", response_model=list[RoomResponse])
async def list_my_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room)
        .where(Room.host_id == current_user.id)
        .order_by(Room.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id, Room.host_id == current_user.id)
        .options(
            selectinload(Room.collection)
            .selectinload(Collection.questions)
            .selectinload(Question.options)
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("/join/{room_code}", response_model=RoomJoinResponse)
async def join_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. Players join by room code."""
    result = await db.execute(
        select(Room).where(Room.room_code == room_code.upper())
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status == RoomStatus.FINISHED:
        raise HTTPException(status_code=400, detail="This game has already ended")

    if room.status == RoomStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Game already in progress")

    return RoomJoinResponse(
        room_id=room.id,
        room_code=room.room_code,
        status=room.status,
        host_id=room.host_id,
    )


@router.patch("/{room_id}/start", response_model=RoomResponse)
async def start_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room).where(Room.id == room_id, Room.host_id == current_user.id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != RoomStatus.WAITING:
        raise HTTPException(status_code=400, detail="Room is not in waiting state")

    room.status = RoomStatus.ACTIVE
    await db.commit()
    await db.refresh(room)
    return room


@router.patch("/{room_id}/end", response_model=RoomResponse)
async def end_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room).where(Room.id == room_id, Room.host_id == current_user.id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != RoomStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Room is not active")

    room.status = RoomStatus.FINISHED
    await db.commit()
    await db.refresh(room)
    return room