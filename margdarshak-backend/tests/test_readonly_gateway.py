import asyncio
import uuid

import pytest
from sqlalchemy import delete, insert, select, update

from app.db.readonly_gateway import ReadOnlyViolationError, execute_readonly
from app.models.placement_drive import PlacementDrive


class FakeAsyncSession:
    def __init__(self) -> None:
        self.executed = False

    async def execute(self, statement):
        self.executed = True
        return statement


@pytest.mark.parametrize(
    "statement",
    [
        insert(PlacementDrive).values(
            id=uuid.uuid4(),
            company_name="Example",
            poc_name="POC",
            poc_contact="poc@example.test",
            policy_doc_ref="policies/example",
            status="active",
        ),
        update(PlacementDrive).values(status="closed"),
        delete(PlacementDrive),
    ],
)
def test_gateway_rejects_write_statements(statement) -> None:
    session = FakeAsyncSession()

    with pytest.raises(ReadOnlyViolationError):
        asyncio.run(execute_readonly(session, statement))

    assert session.executed is False


def test_gateway_allows_select_statement() -> None:
    session = FakeAsyncSession()
    statement = select(PlacementDrive).where(PlacementDrive.id == uuid.uuid4())

    returned = asyncio.run(execute_readonly(session, statement))

    assert returned is statement
    assert session.executed is True
