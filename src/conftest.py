import uuid
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import create_app
from src.core.config import Settings, get_settings
from src.db.base import Base
from src.db.session import get_db
from src.modules.analytics.models.activity import MerchantActivity

_test_settings = get_settings()
DATABASE_URL = _test_settings.test_database_url

engine = create_async_engine(DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

app = create_app()

def get_settings_override() -> Settings:
    return Settings(
        DATABASE_URL=DATABASE_URL,
        API_PORT=_test_settings.test_api_port,
        DATA_DIR="./test_data",
        IMPORT_BATCH_SIZE=10,
    )

app.dependency_overrides[get_settings] = get_settings_override

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        async_session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint"
        )
        yield async_session
        await async_session.close()
        await transaction.rollback()

@pytest.fixture
def override_get_db(db_session: AsyncSession):
    async def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture
async def client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

def make_activity(
    merchant_id: str,
    product: str = "POS",
    status: str = "SUCCESS",
    amount: float | str = 0.0,
    event_type: str = "T",
    event_timestamp: datetime | None = None,
) -> MerchantActivity:
    return MerchantActivity(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        event_timestamp=event_timestamp or datetime.now(),
        product=product,
        event_type=event_type,
        amount=Decimal(str(amount)),
        status=status,
    )
