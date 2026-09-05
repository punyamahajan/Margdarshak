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
from app.models.ticket import Ticket, TicketStatus
from app.models.admin import KnowledgeDocument, StudentNotification, TicketCluster, TicketWorkflow


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
        "university": "Aarohan Demo University",
        "phone": "+91-00000-00611",
        "matchmaking_opt_in": True,
        "tags": ["python", "backend", "placement coordinator"],
    },
    {
        "roll_number": "230622",
        "name": "Diya Test",
        "email": "diya.test@example.invalid",
        "branch": "CSE",
        "university": "Aarohan Demo University",
        "phone": "+91-00000-00622",
        "matchmaking_opt_in": True,
        "tags": ["python", "backend", "coding club"],
    },
    {
        "roll_number": "230633",
        "name": "Ishaan Test",
        "email": "ishaan.test@example.invalid",
        "branch": "ECE",
        "university": "Aarohan Demo University",
        "phone": "+91-00000-00633",
        "matchmaking_opt_in": True,
        "tags": ["robotics", "embedded systems", "coding club"],
    },
    {
        "roll_number": "230644",
        "name": "Mira Test",
        "email": "mira.test@example.invalid",
        "branch": "IT",
        "university": "Aarohan Demo University",
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
    # Coordinator demo data makes the complete admin workflow usable locally
    # without requiring a live Agora call to create its first ticket.
    students = {item.roll_number: item for item in (await session.scalars(select(Student))).all()}
    drives = {item.company_name: item for item in (await session.scalars(select(PlacementDrive))).all()}
    existing_tickets = (await session.scalars(select(Ticket))).all()
    inserted_tickets = 0
    if not existing_tickets:
        cluster = TicketCluster(title="Assessment link issue", company_name="Riverbank Fintech Labs", drive_id=drives["Riverbank Fintech Labs"].id, urgency="critical", status="open", incident_update="The Riverbank assessment link is being verified with the company.")
        session.add(cluster); await session.flush()
        demo_cases = (
            ("230611", "Riverbank Fintech Labs", "Assessment link is not working.", "escalated", "high", "Hindi", "Technical / Assessment", cluster.id),
            ("230622", "Riverbank Fintech Labs", "The assessment page shows an access error.", "open", "high", "English", "Technical / Assessment", cluster.id),
            ("230633", "Acme Cloud Systems", "Can I confirm my eligibility for the online assessment?", "claimed", "medium", "English", "Eligibility", None),
            ("230644", "Northstar Analytics", "I need the updated interview schedule.", "waiting", "medium", "English", "Interview", None),
            ("230611", "Acme Cloud Systems", "The corrected application URL was shared.", "resolved", "low", "English", "Application", None),
        )
        for roll, company, summary, status, urgency, language, category, cluster_id in demo_cases:
            student = students[roll]
            ticket = Ticket(student_id=student.id, drive_id=drives[company].id, issue_summary=summary, transcript_ref=f"demo-{roll}", confidence_score=0.94, status=TicketStatus.ESCALATED if status == "escalated" else TicketStatus.OPEN, escalated_to="demo-placement-support-desk" if status == "escalated" else "", roll_number_snapshot=roll)
            session.add(ticket); await session.flush()
            session.add(TicketWorkflow(ticket_id=ticket.id, status=status, assigned_coordinator="Priya Coordinator" if status == "claimed" else None, urgency=urgency, language=language, category=category, original_request=summary, conversation_summary=f"Student needs verified guidance regarding {company}.", cluster_id=cluster_id))
            inserted_tickets += 1
        session.add(KnowledgeDocument(title="Riverbank Fintech Labs Approved Placement Notice", document_type="placement_policy", company_name="Riverbank Fintech Labs", drive_id=drives["Riverbank Fintech Labs"].id, version_label="2026.1", status="published", source_reference="manual://demo-approved-riverbank", content={"eligibility": "Final-year CSE/IT students; no active backlogs", "deadline": "2026-09-11", "instructions": "Use the approved placement portal link."}))
        session.add(KnowledgeDocument(title="Resolved issue: Riverbank assessment link", document_type="resolved_issue", company_name="Riverbank Fintech Labs", version_label="2026.1", status="published", source_reference="coordinator://demo-resolution", content={"resolution": "The company re-issued the assessment link.", "response": "Use the newly shared link from the placement portal."}))
        await session.commit()
    return {
        "drives_inserted": len(new_drives),
        "drives_existing": len(PLACEMENT_DRIVES) - len(new_drives),
        "students_inserted": len(new_students),
        "students_existing": len(STUDENTS) - len(new_students),
        "demo_tickets_inserted": inserted_tickets,
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
