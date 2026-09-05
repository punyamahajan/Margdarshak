import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.api.v1.routes_admin import _normalize_shortlist_row, _parse_shortlist


def test_shortlist_csv_is_normalized_and_validated() -> None:
    content = (
        "Name,enrollment_number,email,company,drive_id,shortlisted,role,round\n"
        "Aarav Sharma,230611,aarav@example.edu,Riverbank,drive-1,yes,ASE,Technical\n"
    )
    upload = UploadFile(filename="shortlist.csv", file=BytesIO(content.encode()))
    rows = asyncio.run(_parse_shortlist(upload))
    assert rows[0]["name"] == "Aarav Sharma"
    assert rows[0]["shortlisted"] == "yes"


def test_shortlist_rejects_missing_columns() -> None:
    upload = UploadFile(filename="shortlist.csv", file=BytesIO(b"name,email\nA,a@example.edu\n"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(_parse_shortlist(upload))
    assert error.value.status_code == 422


def test_shortlist_values_are_trimmed() -> None:
    row = _normalize_shortlist_row({" Name ": " Aarav ", "shortlisted": True})
    assert row == {"name": "Aarav", "shortlisted": "True"}
