"""Test configuration and fixtures"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.modules.users.repository import ensure_indexes as ensure_users_indexes
from app.modules.wallets.repository import ensure_indexes as ensure_wallets_indexes
from app.modules.ledger.repository import ensure_indexes as ensure_ledger_indexes

TEST_DATABASE_NAME = "mini_wallet_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_client():
    """Function-scoped AsyncIOMotorClient to connect to the DB."""
    client = AsyncIOMotorClient(settings.MONGODB_URL, uuidRepresentation="standard")
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(db_client):
    """
    Function-scoped database fixture that drops the test database 
    after each test run to ensure complete test isolation.
    """
    import uuid
    unique_db_name = f"mw_{uuid.uuid4().hex[:8]}"
    db = db_client[unique_db_name]
    # Build indexes for testing
    await ensure_users_indexes(db)
    await ensure_wallets_indexes(db)
    await ensure_ledger_indexes(db)
    yield db
    # Cleanup after test function executes
    await db_client.drop_database(unique_db_name)


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """
    Test client for FastAPI app with overridden database dependency.
    """
    def override_get_db():
        return test_db

    # Override get_db dependency in app
    app.dependency_overrides[get_db] = override_get_db
    
    import typing
    # Cast app to Any to resolve Pyright type checking warning
    transport = ASGITransport(app=typing.cast(typing.Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    # Remove override
    app.dependency_overrides.pop(get_db, None)
