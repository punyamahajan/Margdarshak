import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.routes_admin import (
    KnowledgeStatusUpdate,
    KnowledgeWrite,
    create_knowledge,
    list_knowledge,
    update_knowledge,
)
from app.models.admin import KnowledgeDocument


def test_create_knowledge_draft_policy() -> None:
    mock_db = AsyncMock()
    payload = KnowledgeWrite(
        title="Acme Cloud Systems Placement Notice",
        document_type="placement_policy",
        company_name="Acme Cloud Systems",
        version_label="2026.1",
        source_reference="manual://coordinator-entry",
        status="draft",
        content={
            "eligibility": "Final-year CSE/IT, CGPA 7.5+",
            "salary_ctc": "14 LPA",
            "deadline": "2026-09-30",
            "application_url": "https://careers.acme.com/apply",
            "instructions": "Submit application before deadline.",
        },
    )

    resp = asyncio.run(create_knowledge(payload, db=mock_db))
    assert "id" in resp
    assert resp["status"] == "draft"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_list_knowledge() -> None:
    mock_db = AsyncMock()
    doc = KnowledgeDocument(
        id=uuid.uuid4(),
        title="Acme Cloud Systems Placement Notice",
        document_type="placement_policy",
        company_name="Acme Cloud Systems",
        version_label="2026.1",
        status="draft",
        source_reference="manual://coordinator-entry",
        content={"eligibility": "Final-year"},
    )
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [doc]
    mock_db.scalars.return_value = scalars_mock

    results = asyncio.run(list_knowledge(db=mock_db))
    assert len(results) == 1
    assert results[0]["title"] == "Acme Cloud Systems Placement Notice"
    assert results[0]["status"] == "draft"


def test_update_knowledge_lifecycle() -> None:
    mock_db = AsyncMock()
    doc_id = uuid.uuid4()
    doc = KnowledgeDocument(
        id=doc_id,
        title="Acme Cloud Systems Placement Notice",
        document_type="placement_policy",
        status="draft",
        version_label="2026.1",
        source_reference="manual://test",
    )
    mock_db.get.return_value = doc

    # 1. Update from draft to published via query param
    resp1 = asyncio.run(update_knowledge(doc_id, status="published", db=mock_db))
    assert resp1["status"] == "published"
    assert doc.status == "published"

    # 2. Update from published to expired via payload
    resp2 = asyncio.run(update_knowledge(doc_id, payload=KnowledgeStatusUpdate(status="expired"), db=mock_db))
    assert resp2["status"] == "expired"
    assert doc.status == "expired"

    # 3. Invalid status raises 400
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(update_knowledge(doc_id, status="invalid_status", db=mock_db))
    assert excinfo.value.status_code == 400


def test_shortlist_preview_valid_csv() -> None:
    from io import BytesIO
    from fastapi import UploadFile
    from app.api.v1.routes_admin import shortlist_preview

    csv_content = (
        "name,enrollment_number,email,company,drive_id,shortlisted,role,round\n"
        "Aarav Sharma,230611,aarav@example.edu,Riverbank,drive-1,yes,SDE,Technical\n"
    )
    upload = UploadFile(filename="shortlist.csv", file=BytesIO(csv_content.encode("utf-8")))
    res = asyncio.run(shortlist_preview(upload))
    assert res["valid"] is True
    assert res["record_count"] == 1
    assert res["rows"][0]["name"] == "Aarav Sharma"
    assert res["rows"][0]["shortlisted"] == "yes"


def test_shortlist_preview_missing_required_fields_422() -> None:
    from io import BytesIO
    from fastapi import UploadFile
    from app.api.v1.routes_admin import shortlist_preview

    csv_content = "name,email\nAarav,aarav@example.edu\n"
    upload = UploadFile(filename="shortlist.csv", file=BytesIO(csv_content.encode("utf-8")))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(shortlist_preview(upload))
    assert exc.value.status_code == 422
    assert "missing required shortlist columns" in exc.value.detail["message"]


def test_shortlist_preview_invalid_format_400() -> None:
    from io import BytesIO
    from fastapi import UploadFile
    from app.api.v1.routes_admin import shortlist_preview

    upload = UploadFile(filename="shortlist.txt", file=BytesIO(b"random text"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(shortlist_preview(upload))
    assert exc.value.status_code == 400


def test_shortlist_import_creates_records() -> None:
    from app.api.v1.routes_admin import ShortlistImportConfirm, shortlist_import

    mock_db = AsyncMock()
    payload = ShortlistImportConfirm(
        title="Riverbank Shortlist Round 1",
        source_reference="spreadsheet://test",
        version_label="2026.1",
        rows=[
            {
                "name": "Aarav Sharma",
                "enrollment_number": "230611",
                "email": "aarav@example.edu",
                "company": "Riverbank",
                "drive_id": "drive-1",
                "shortlisted": "yes",
                "role": "SDE",
                "round": "Technical",
            }
        ],
    )
    res = asyncio.run(shortlist_import(payload, db=mock_db))
    assert "document_id" in res
    assert res["imported"] == 1
    assert res["status"] == "published"
    assert mock_db.add.called
    assert mock_db.add_all.called
    assert mock_db.commit.called


def test_admin_stats_returns_all_spec_metrics() -> None:
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.api.v1.routes_admin import admin_stats_spec

    mock_db = AsyncMock()
    mock_tickets = [
        {
            "id": "1",
            "status": "resolved",
            "student": {"enrollment_number": "230001"},
            "intelligence": {"category": "Eligibility Issue", "language": "English"},
            "placement": {"company": "Acme Corp"},
            "created_at": datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        },
        {
            "id": "2",
            "status": "open",
            "student": {"enrollment_number": "230002"},
            "intelligence": {"category": "Portal Error", "language": "Hindi"},
            "placement": {"company": "Riverbank"},
            "created_at": datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 9, 2, 11, 0, tzinfo=timezone.utc),
        },
    ]
    mock_clusters = [
        {"id": "c1", "status": "open"},
    ]

    with patch("app.api.v1.routes_admin.list_admin_tickets", AsyncMock(return_value=mock_tickets)), \
         patch("app.api.v1.routes_admin.list_clusters", AsyncMock(return_value=mock_clusters)):
        res = asyncio.run(admin_stats_spec(db=mock_db))

    assert res["total_conversations"] == 2
    assert res["tickets_created"] == 2
    assert res["tickets_resolved"] == 1
    assert res["students_assisted"] == 2
    assert res["active_clusters"] == 1
    assert res["average_resolution_time_hours"] == 2.0
    assert "Eligibility Issue" in res["most_common_issue_categories"]
    assert "Acme Corp" in res["most_requested_companies"]
    assert "English" in res["most_common_languages"]


