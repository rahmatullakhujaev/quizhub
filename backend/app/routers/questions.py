import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.option import Option
from app.core.deps import get_current_user
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = Question(
        text=body.text,
        time_limit=body.time_limit,
        creator_id=current_user.id,
    )
    db.add(question)
    await db.flush()  

    for opt in body.options:
        option = Option(
            text=opt.text,
            is_correct=opt.is_correct,
            question_id=question.id,
        )
        db.add(option)

    await db.commit()

    # reload with options
    result = await db.execute(
        select(Question).where(Question.id == question.id).options(selectinload(Question.options))
    )
    return result.scalar_one()


@router.get("/", response_model=list[QuestionResponse])
async def list_my_questions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question)
        .where(Question.creator_id == current_user.id)
        .options(selectinload(Question.options))
        .order_by(Question.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id, Question.creator_id == current_user.id)
        .options(selectinload(Question.options))
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    body: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id, Question.creator_id == current_user.id)
        .options(selectinload(Question.options))
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if body.text is not None:
        question.text = body.text
    if body.time_limit is not None:
        question.time_limit = body.time_limit

    if body.options is not None:
        # delete old options, replace with new
        for old_opt in question.options:
            await db.delete(old_opt)
        await db.flush()

        for opt in body.options:
            option = Option(
                text=opt.text,
                is_correct=opt.is_correct,
                question_id=question.id,
            )
            db.add(option)

    await db.commit()

    # reload
    result = await db.execute(
        select(Question).where(Question.id == question.id).options(selectinload(Question.options))
    )
    return result.scalar_one()


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Question).where(Question.id == question_id, Question.creator_id == current_user.id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()