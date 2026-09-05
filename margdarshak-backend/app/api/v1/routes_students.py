import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.admin import ShortlistRecord, StudentNotification
from app.models.student import Student
from app.services.knowledge_service import retrieve_approved_knowledge

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}")
async def get_student(student_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "student not found")
    return {"id": str(student.id), "name": student.name, "enrollment_number": student.roll_number, "email": student.email, "branch": student.branch, "university": student.university}


@router.get("/{student_id}/placements")
async def get_student_placements(student_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> list[dict[str, object]]:
    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "student not found")
    records = (await db.scalars(select(ShortlistRecord).where((ShortlistRecord.enrollment_number == student.roll_number) | (ShortlistRecord.email == student.email)))).all()
    return [{"company": record.company_name, "drive_id": record.drive_id, "role": record.role, "round": record.round, "shortlisted": record.shortlisted, "source": "Imported approved shortlist"} for record in records]


@router.get("/{student_id}/notifications")
async def get_student_notifications(student_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> list[dict[str, object]]:
    notifications = (await db.scalars(select(StudentNotification).where(StudentNotification.student_id == student_id).order_by(StudentNotification.created_at.desc()))).all()
    return [{"id": str(item.id), "title": item.title, "body": item.body, "ticket_id": str(item.ticket_id) if item.ticket_id else None, "created_at": item.created_at} for item in notifications]


@router.get("/{student_id}/knowledge")
async def search_student_knowledge(student_id: uuid.UUID, query: str, company: str | None = None, db: AsyncSession = Depends(get_db_session)) -> list[dict[str, object]]:
    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "student not found")
    return await retrieve_approved_knowledge(db, query, company=company, enrollment_number=student.roll_number)
