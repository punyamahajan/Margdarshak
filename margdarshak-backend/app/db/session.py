from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.readonly_gateway import install_readonly_guards
from app.db.session_factory import get_session_factory

install_readonly_guards()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
