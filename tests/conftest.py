import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional database session that rolls back after each test."""
    # Create engine per test to avoid event-loop mismatch
    test_engine = create_async_engine(get_settings().database_url)
    async with test_engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Override commit to no-op (controllers already flush)
        async def _noop_commit() -> None:
            pass

        session.commit = _noop_commit  # type: ignore[method-assign]

        async def override_get_db() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_db] = override_get_db

        yield session

        await session.close()
        await txn.rollback()
    await test_engine.dispose()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        display_name="Test User",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authenticated_client(
    auth_headers: dict[str, str],
) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", headers=auth_headers
    ) as c:
        yield c
