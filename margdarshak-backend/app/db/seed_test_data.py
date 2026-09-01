"""Seed deterministic local data for end-to-end call and matchmaker testing.

Run from the backend directory after applying migrations:

    python -m app.db.seed_test_data
"""

import asyncio
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session_factory import get_session_factory
from app.models.placement_drive import PlacementDrive
from app.models.student import Student


PLACEMENT_DRIVES: tuple[dict[str, str], ...] = (
    {
        "company_name": "Acme Cloud Systems",
        "poc_name": "Test POC - Ananya",
        "poc_contact": "agora-test-poc-acme-not-reachable",
        "policy_doc_ref": (
            "Round 1: online assessment, Round 2: technical interview, "
            "Round 3: HR"
        ),
        "status": "active",
    },
    {
        "company_name": "Northstar Analytics",
        "poc_name": "Test POC - Kabir",
        "poc_contact": "agora-test-poc-northstar-not-reachable",
        "policy_doc_ref": (
            "Minimum CGPA: 7.0, Round 1: aptitude test, Round 2: data case study"
        ),
        "status": "active",
    },
    {
        "company_name": "Riverbank Fintech Labs",
        "poc_name": "Test POC - Meera",
        "poc_contact": "agora-test-poc-riverbank-not-reachable",
        "policy_doc_ref": (
            "Round 1: coding test, Round 2: system design, no active backlogs"
        ),
        "status": "active",
    },
    {
        "company_name": "Greenfield Robotics",
        "poc_name": "Test POC - Arjun",
        "poc_contact": "agora-test-poc-greenfield-not-reachable",
        "policy_doc_ref": (
            "Round 1: resume shortlist, Round 2: robotics task, Round 3: panel"
        ),
        "status": "active",
    },
)


STUDENTS: tuple[dict[str, object], ...] = (
    {
        "roll_number": "230611",
        "name": "Aarav Test",
        "email": "aarav.test@example.invalid",
        "branch": "CSE",
        "phone": "+91-00000-00611",
        "matchmaking_opt_in": True,
        "tags": ["python", "backend", "placement coordinator"],
    },
    {
        "roll_number": "230622",
        "name": "Diya Test",
        "email": "diya.test@example.invalid",
        "branch": "CSE",
        "phone": "+91-00000-00622",
        "matchmaking_opt_in": True,
        "tags": ["python", "backend", "coding club"],
    },
    {
        "roll_number": "230633",
        "name": "Ishaan Test",
        "email": "ishaan.test@example.invalid",
        "branch": "ECE",
        "phone": "+91-00000-00633",
        "matchmaking_opt_in": True,
        "tags": ["robotics", "embedded systems", "coding club"],
    },
    {
        "roll_number": "230644",
        "name": "Mira Test",
        "email": "mira.test@example.invalid",
        "branch": "IT",
        "phone": "+91-00000-00644",
        "matchmaking_opt_in": False,
        "tags": ["data analytics", "event volunteer", "public speaking"],
    },
)


async def _existing_values(
    session: AsyncSession, column: object, values: Sequence[str]
) -> set[str]:
    return set((await session.scalars(select(column).where(column.in_(values)))).all())


async def seed_test_data(session: AsyncSession) -> dict[str, int]:
    """Insert missing fixtures, using natural identifiers for idempotency."""

    company_names = [drive["company_name"] for drive in PLACEMENT_DRIVES]
    existing_companies = await _existing_values(
        session, PlacementDrive.company_name, company_names
    )
    new_drives = [
        PlacementDrive(**drive)
        for drive in PLACEMENT_DRIVES
        if drive["company_name"] not in existing_companies
    ]

    roll_numbers = [str(student["roll_number"]) for student in STUDENTS]
    existing_roll_numbers = await _existing_values(
        session, Student.roll_number, roll_numbers
    )
    new_students = [
        Student(**student)
        for student in STUDENTS
        if student["roll_number"] not in existing_roll_numbers
    ]

    session.add_all([*new_drives, *new_students])
    await session.commit()
    return {
        "drives_inserted": len(new_drives),
        "drives_existing": len(PLACEMENT_DRIVES) - len(new_drives),
        "students_inserted": len(new_students),
        "students_existing": len(STUDENTS) - len(new_students),
    }


async def main() -> None:
    async with get_session_factory()() as session:
        result = await seed_test_data(session)

    print(
        "Test data ready: "
        f"{result['drives_inserted']} drives inserted, "
        f"{result['drives_existing']} already present; "
        f"{result['students_inserted']} students inserted, "
        f"{result['students_existing']} already present."
    )


if __name__ == "__main__":
    asyncio.run(main())
