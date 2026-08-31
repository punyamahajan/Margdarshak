"""SELECT-only access to externally synced placement drives."""

import uuid
from typing import Any

from sqlalchemy import Delete, Insert, Select, Update, event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from app.db.session_factory import get_session_factory
from app.models.placement_drive import PlacementDrive


class ReadOnlyViolationError(RuntimeError):
    """Raised when application code attempts to mutate a read-only table."""


# Backward-compatible name for callers of the original guard.
ReadOnlyTableError = ReadOnlyViolationError


def _raise_readonly_error() -> None:
    raise ReadOnlyViolationError(
        "placement_drives is externally synced and read-only to application code"
    )


def _ensure_select(statement: Any) -> None:
    if not isinstance(statement, Select):
        _raise_readonly_error()


async def execute_readonly(session: AsyncSession, statement: Any):
    """Execute only SELECT statements through this gateway."""

    _ensure_select(statement)
    return await session.execute(statement)


async def query_drive_policy(drive_id: uuid.UUID) -> dict[str, Any]:
    """Return policy context for one externally synced placement drive."""

    statement = select(PlacementDrive).where(PlacementDrive.id == drive_id)
    async with get_session_factory()() as session:
        result = await execute_readonly(session, statement)
        drive = result.scalar_one_or_none()

    if drive is None:
        return {}

    return {
        "id": str(drive.id),
        "company_name": drive.company_name,
        "poc_name": drive.poc_name,
        "poc_contact": drive.poc_contact,
        "policy_doc_ref": drive.policy_doc_ref,
        "status": drive.status,
    }


def _guard_orm_flush(session: Session, *_: object) -> None:
    pending = session.new.union(session.dirty).union(session.deleted)
    if any(isinstance(instance, PlacementDrive) for instance in pending):
        _raise_readonly_error()


def _guard_explicit_statement(execute_state: ORMExecuteState) -> None:
    statement = execute_state.statement
    if isinstance(statement, (Insert, Update, Delete)):
        table = getattr(statement, "table", None)
        if table is not None and table.name == PlacementDrive.__tablename__:
            _raise_readonly_error()


def install_readonly_guards() -> None:
    """Install guards on the synchronous session underlying AsyncSession."""

    if not event.contains(Session, "before_flush", _guard_orm_flush):
        event.listen(Session, "before_flush", _guard_orm_flush)
    if not event.contains(Session, "do_orm_execute", _guard_explicit_statement):
        event.listen(Session, "do_orm_execute", _guard_explicit_statement)
