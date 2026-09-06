"""Authentication and Student Profile Routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.student import Student
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class StudentSignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)
    college_name: str = Field(min_length=1, max_length=255)
    student_id: str = Field(min_length=1, max_length=50)
    branch: str = Field(default="Computer Science", max_length=100)
    phone: str = Field(default="", max_length=30)
    known_subjects: list[str] = Field(default_factory=list)
    explore_topics: list[str] = Field(default_factory=list)
    linkedin_url: str | None = None


class StudentLoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class StudentProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    college_name: str
    student_id: str
    branch: str
    phone: str
    known_subjects: list[str]
    explore_topics: list[str]
    tags: list[str]
    linkedin_url: str | None
    matchmaking_opt_in: bool

    @classmethod
    def from_student(cls, student: Student) -> StudentProfileResponse:
        return cls(
            id=student.id,
            name=student.name,
            email=student.email,
            college_name=student.university,
            student_id=student.roll_number,
            branch=student.branch,
            phone=student.phone or "",
            known_subjects=student.known_subjects or [],
            explore_topics=student.explore_topics or [],
            tags=student.tags or [],
            linkedin_url=student.linkedin_url,
            matchmaking_opt_in=student.matchmaking_opt_in,
        )


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student: StudentProfileResponse


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    college_name: str | None = None
    branch: str | None = None
    known_subjects: list[str] | None = None
    explore_topics: list[str] | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    matchmaking_opt_in: bool | None = None


async def get_current_student(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> Student:
    """Dependency to retrieve the authenticated student via Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        student_uuid = uuid.UUID(payload["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
        )

    student = await db.scalar(select(Student).where(Student.id == student_uuid))
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student not found",
        )
    return student


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: StudentSignupRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    """Register a new student profile with college, ID, subjects, and topics to explore."""
    clean_email = str(payload.email).strip().lower()
    clean_roll = payload.student_id.strip()

    # Check uniqueness of email or roll_number
    existing = await db.scalar(
        select(Student).where(
            or_(Student.email == clean_email, Student.roll_number == clean_roll)
        )
    )
    if existing:
        if existing.email == clean_email:
            raise HTTPException(status_code=409, detail="A student with this email already exists")
        raise HTTPException(status_code=409, detail="A student with this Student ID / Roll Number already exists")

    # Sync tags with known_subjects + explore_topics
    combined_tags = list(dict.fromkeys(payload.known_subjects + payload.explore_topics))

    student = Student(
        name=payload.name.strip(),
        email=clean_email,
        roll_number=clean_roll,
        university=payload.college_name.strip(),
        branch=payload.branch.strip(),
        phone=payload.phone.strip(),
        password_hash=hash_password(payload.password),
        known_subjects=payload.known_subjects,
        explore_topics=payload.explore_topics,
        tags=combined_tags,
        linkedin_url=payload.linkedin_url.strip() if payload.linkedin_url else None,
        matchmaking_opt_in=True,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)

    token = create_access_token({"sub": str(student.id), "email": student.email})
    return AuthTokenResponse(
        access_token=token,
        student=StudentProfileResponse.from_student(student),
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: StudentLoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    """Sign in an existing student via email or student ID."""
    clean_identifier = payload.email.strip().lower()
    student = await db.scalar(
        select(Student).where(
            or_(
                Student.email == clean_identifier,
                Student.roll_number == payload.email.strip(),
            )
        )
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/ID or password",
        )

    # If student exists without password (e.g. legacy seeded), initialize password
    if not student.password_hash:
        student.password_hash = hash_password(payload.password)
        await db.commit()
    elif not verify_password(payload.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/ID or password",
        )

    token = create_access_token({"sub": str(student.id), "email": student.email})
    return AuthTokenResponse(
        access_token=token,
        student=StudentProfileResponse.from_student(student),
    )


@router.get("/me", response_model=StudentProfileResponse)
async def get_my_profile(
    current_student: Student = Depends(get_current_student),
) -> StudentProfileResponse:
    """Return the profile of the currently signed-in student."""
    return StudentProfileResponse.from_student(current_student)


@router.put("/profile", response_model=StudentProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db_session),
) -> StudentProfileResponse:
    """Update subjects, explore topics, college name, or details for the signed-in student."""
    if payload.name is not None:
        current_student.name = payload.name.strip()
    if payload.college_name is not None:
        current_student.university = payload.college_name.strip()
    if payload.branch is not None:
        current_student.branch = payload.branch.strip()
    if payload.phone is not None:
        current_student.phone = payload.phone.strip()
    if payload.linkedin_url is not None:
        current_student.linkedin_url = payload.linkedin_url.strip() if payload.linkedin_url else None
    if payload.matchmaking_opt_in is not None:
        current_student.matchmaking_opt_in = payload.matchmaking_opt_in

    if payload.known_subjects is not None:
        current_student.known_subjects = [s.strip() for s in payload.known_subjects if s.strip()]
    if payload.explore_topics is not None:
        current_student.explore_topics = [t.strip() for t in payload.explore_topics if t.strip()]

    # Keep tags updated with all known and exploration skills
    current_student.tags = list(dict.fromkeys(
        (current_student.known_subjects or []) + (current_student.explore_topics or [])
    ))

    await db.commit()
    await db.refresh(current_student)
    return StudentProfileResponse.from_student(current_student)
