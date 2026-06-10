"""Test configuration and fixtures"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.database import get_db
from app.main import app

# Set VECTOR_STORE to atlas during tests to query the isolated test MongoDB database (local manual search fallback)
settings.VECTOR_STORE = "atlas"
settings.OPENAI_API_KEY = "your_openai_api_key_here"
settings.LANGSMITH_TRACING = False

TEST_DATABASE_NAME = "vsmartpay_test"

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
    unique_db_name = f"vp_{uuid.uuid4().hex[:8]}"
    db = db_client[unique_db_name]
    yield db
    # Cleanup after test function executes
    try:
        await db_client.drop_database(unique_db_name)
    except Exception as e:
        print(f"Warning: Failed to drop test database {unique_db_name}: {e}")


@pytest_asyncio.fixture(scope="function", autouse=True)
async def seed_knowledge_chunks(test_db):
    """
    Autouse fixture that seeds mock RAG knowledge chunks into the test database 
    so retriever queries find valid chunks.
    """
    col = test_db["knowledge_chunks"]
    await col.insert_many([
        {
            "chunk_id": "chk_limit_01",
            "doc_id": "limits.md",
            "file_name": "limits.md",
            "category": "Hạn mức",
            "content": "Hạn mức giao dịch tối đa qua ví VSmartPay là 50.000.000 VND/ngày đối với tài khoản đã KYC.",
            "embedding": [0.01] * 1536,
            "kb_type": "policy",
            "agent_scope": "limits",
            "language": "vi"
        },
        {
            "chunk_id": "chk_fraud_01",
            "doc_id": "security.md",
            "file_name": "security.md",
            "category": "Bảo mật",
            "content": "Nếu nghi ngờ bị lừa đảo hoặc mất tiền, khách hàng cần báo cáo ngay lập tức để khóa tài khoản.",
            "embedding": [0.01] * 1536,
            "kb_type": "policy",
            "agent_scope": "security",
            "language": "vi"
        }
    ])


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db(test_db):
    """
    Autouse fixture that sets db_manager.db to the isolated test database 
    for each test function, resolving database availability issues.
    """
    from app.database import db_manager
    db_manager.db = test_db
    yield
    db_manager.db = None


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """
    Test client for FastAPI app with overridden database dependency.
    """
    def override_get_db():
        return test_db

    from fastapi import Request
    from app.common.security import get_current_user
    from app.modules.users.schema import UserResponse

    async def override_get_current_user(request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header and "Bearer bad_token_here" not in auth_header:
            from jose import jwt
            from app.config import settings
            from app.modules.users.repository import UsersRepository
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
                if user_id:
                    user = await UsersRepository().get_user_by_id(user_id)
                    if user:
                        return UserResponse(**user)
            except Exception as e:
                print(f"Exception in get_current_user override: {e}")
                pass
        
        # If no auth header is provided and the path is /chat, return a mock default user for backwards compatibility with tests
        if not auth_header and request.url.path == "/chat":
            user_id = "user_001"
            try:
                body = await request.json()
                if isinstance(body, dict) and body.get("user_id"):
                    user_id = body["user_id"]
            except Exception:
                pass
            return UserResponse(
                user_id=user_id,
                full_name="Mock User",
                phone="0900000000",
                email="mock@example.com",
                kyc_status="UNVERIFIED",
                created_at="2026-06-02T08:18:41Z"
            )
            
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Override get_db and get_current_user dependencies in app
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    import typing
    # Cast app to Any to resolve Pyright type checking warning
    transport = ASGITransport(app=typing.cast(typing.Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    # Remove overrides
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
