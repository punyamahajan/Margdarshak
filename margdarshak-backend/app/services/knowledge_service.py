import json
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import KnowledgeDocument, ShortlistRecord

KNOWLEDGE_PRIORITY = {"resolved_issue": 1, "company_information": 2, "placement_drive": 2, "placement_policy": 3, "shortlist": 4}


def knowledge_rank(document_type: str) -> int:
    return KNOWLEDGE_PRIORITY.get(document_type, 5)


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


async def retrieve_approved_knowledge(db: AsyncSession, query: str, *, company: str | None = None, enrollment_number: str | None = None) -> list[dict[str, Any]]:
    statement = select(KnowledgeDocument).where(KnowledgeDocument.status == "published")
    if company:
        statement = statement.where(KnowledgeDocument.company_name == company)
    documents = (await db.scalars(statement)).all()
    query_terms = _terms(query)
    matches = []
    for document in documents:
        searchable = f"{document.title} {document.company_name or ''} {json.dumps(document.content or {})}"
        overlap = len(query_terms & _terms(searchable))
        if overlap or not query_terms:
            matches.append((knowledge_rank(document.document_type), -overlap, document))
    matches.sort(key=lambda item: (item[0], item[1], -item[2].created_at.timestamp()))
    results = [{"id": str(doc.id), "title": doc.title, "type": doc.document_type, "company": doc.company_name, "version": doc.version_label, "source": doc.source_reference, "content": doc.content} for _, _, doc in matches]
    if enrollment_number:
        shortlist = (await db.scalars(select(ShortlistRecord).where(ShortlistRecord.enrollment_number == enrollment_number))).all()
        results.extend({"id": str(record.id), "title": f"{record.company_name} shortlist", "type": "shortlist", "company": record.company_name, "version": "imported", "source": "approved-shortlist", "content": {"shortlisted": record.shortlisted, "role": record.role, "round": record.round, "drive_id": record.drive_id}} for record in shortlist)
    return results
