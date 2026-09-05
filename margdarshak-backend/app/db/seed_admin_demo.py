"""Create local-only coordinator demo data after the standard seed scripts.

Run: python -m app.db.seed_admin_demo
"""
import asyncio

from sqlalchemy import select

from app.db.session_factory import get_session_factory
from app.models.admin import KnowledgeDocument, TicketCluster, TicketWorkflow
from app.models.placement_drive import PlacementDrive
from app.models.student import Student
from app.models.ticket import Ticket, TicketStatus


async def main() -> None:
    async with get_session_factory()() as session:
        existing = await session.scalar(select(Ticket.id).where(Ticket.transcript_ref == "admin-demo-1"))
        if existing:
            print("Admin demo data already exists.")
            return
        students = (await session.scalars(select(Student).order_by(Student.roll_number).limit(4))).all()
        drives = (await session.scalars(select(PlacementDrive).order_by(PlacementDrive.company_name).limit(3))).all()
        if len(students) < 4 or len(drives) < 3:
            raise RuntimeError("Run seed_test_data before seed_admin_demo")
        cluster = TicketCluster(title="Assessment link issue", company_name="Riverbank Fintech Labs", drive_id=drives[2].id, urgency="high", status="open")
        session.add(cluster); await session.flush()
        cases = [
            ("admin-demo-1", students[0], drives[2], "Assessment link is not working.", "escalated", "critical", "Hindi", cluster.id),
            ("admin-demo-2", students[1], drives[2], "Riverbank test portal keeps timing out.", "open", "high", "English", cluster.id),
            ("admin-demo-3", students[2], drives[0], "Please confirm my eligibility for the assessment.", "claimed", "medium", "English", None),
            ("admin-demo-4", students[3], drives[1], "Shortlist record needs verification.", "waiting", "medium", "English", None),
            ("admin-demo-5", students[0], drives[0], "Application URL was corrected and shared.", "resolved", "low", "Hindi", None),
        ]
        for ref, student, drive, summary, workflow_status, urgency, language, cluster_id in cases:
            ticket = Ticket(student_id=student.id, drive_id=drive.id, issue_summary=summary, transcript_ref=ref, confidence_score=0.94, status=TicketStatus.ESCALATED if workflow_status == "escalated" else TicketStatus.OPEN, escalated_to="demo-placement-desk", roll_number_snapshot=student.roll_number)
            session.add(ticket); await session.flush()
            session.add(TicketWorkflow(ticket_id=ticket.id, status=workflow_status, urgency=urgency, language=language, category="Assessment" if cluster_id else "Eligibility", assigned_coordinator="Meera Kapoor" if workflow_status in {"claimed", "escalated"} else None, cluster_id=cluster_id, original_request=summary, conversation_summary=f"Student reported: {summary}"))
        session.add(KnowledgeDocument(title="Riverbank Fintech Labs Approved Placement Notice", document_type="placement_policy", company_name="Riverbank Fintech Labs", drive_id=drives[2].id, version_label="2026.1", status="published", source_reference="manual://demo-approved-policy", content={"eligibility": "Final-year CSE/IT, CGPA 7.5+, no active backlogs", "deadline": "2026-09-11"}))
        await session.commit()
        print("Admin demo data created: 5 tickets, 1 cluster, 1 published policy.")


if __name__ == "__main__":
    asyncio.run(main())
