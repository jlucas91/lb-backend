import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.core.storage import ObjectMeta, S3StorageService, get_storage
from app.main import app
from app.models import Base
from app.models.user import User


@pytest.fixture(scope="session", autouse=True)
async def _create_tables() -> AsyncIterator[None]:
    """Recreate all tables once per test session to match current models."""
    from sqlalchemy import text

    db_url = get_settings().database_url

    # Ensure the test database exists by connecting to the default 'postgres' db
    admin_url = db_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'locationsbook_test'")
        )
        if not result.scalar():
            await conn.execute(text("CREATE DATABASE locationsbook_test"))
    await admin_engine.dispose()

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        # Drop legacy tables that may have stale FK constraints
        await conn.execute(text("DROP TABLE IF EXISTS files CASCADE"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


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


@pytest.fixture(autouse=True)
def mock_storage() -> AsyncMock:
    """Override get_storage with an AsyncMock for all tests."""
    mock = AsyncMock(spec=S3StorageService)
    mock.generate_storage_key.return_value = "uploads/test-uuid/photo.jpg"
    mock.generate_upload_url.return_value = "https://s3.example.com/presigned-put"
    mock.generate_download_url.return_value = "https://s3.example.com/presigned-get"
    mock.head_object.return_value = ObjectMeta(
        content_type="image/jpeg", content_length=12345
    )
    mock.delete_object.return_value = None

    app.dependency_overrides[get_storage] = lambda: mock

    yield mock  # type: ignore[misc]

    app.dependency_overrides.pop(get_storage, None)


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


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        display_name="Other User",
        password_hash=hash_password("otherpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def other_auth_headers(other_user: User) -> dict[str, str]:
    token = create_access_token(str(other_user.id))
    return {"Authorization": f"Bearer {token}"}
