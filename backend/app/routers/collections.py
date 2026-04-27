import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.collection import Collection
from app.core.deps import get_current_user
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionResponse, CollectionListResponse

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
   
    result = await db.execute(
        select(Question)
        .where(Question.id.in_(body.question_ids), Question.creator_id == current_user.id)
        .options(selectinload(Question.options))
    )
    questions = result.scalars().all()

    if len(questions) != len(body.question_ids):
        raise HTTPException(status_code=400, detail="Some questions not found or don't belong to you")

    collection = Collection(
        title=body.title,
        creator_id=current_user.id,
    )
    collection.questions = list(questions)
    db.add(collection)
    await db.commit()

    # reload with relationships
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection.id)
        .options(selectinload(Collection.questions).selectinload(Question.options))
    )
    return result.scalar_one()


@router.get("/", response_model=list[CollectionListResponse])
async def list_my_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection)
        .where(Collection.creator_id == current_user.id)
        .options(selectinload(Collection.questions))
        .order_by(Collection.created_at.desc())
    )
    collections = result.scalars().all()

    return [
        CollectionListResponse(
            id=c.id,
            title=c.title,
            creator_id=c.creator_id,
            created_at=c.created_at,
            question_count=len(c.questions),
        )
        for c in collections
    ]


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.creator_id == current_user.id)
        .options(selectinload(Collection.questions).selectinload(Question.options))
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: uuid.UUID,
    body: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.creator_id == current_user.id)
        .options(selectinload(Collection.questions))
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if body.title is not None:
        collection.title = body.title

    if body.question_ids is not None:
        result = await db.execute(
            select(Question)
            .where(Question.id.in_(body.question_ids), Question.creator_id == current_user.id)
            .options(selectinload(Question.options))
        )
        questions = result.scalars().all()

        if len(questions) != len(body.question_ids):
            raise HTTPException(status_code=400, detail="Some questions not found or don't belong to you")

        collection.questions = list(questions)

    await db.commit()

    # reload
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection.id)
        .options(selectinload(Collection.questions).selectinload(Question.options))
    )
    return result.scalar_one()


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection).where(Collection.id == collection_id, Collection.creator_id == current_user.id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    await db.delete(collection)
    await db.commit()