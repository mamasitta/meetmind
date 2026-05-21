import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.schemas.meeting import MeetingExtraction, ActionItem, Decision, Risk


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_transcript():
    return """Alice: Good morning. Bob, can you finish the login page by Friday?
Bob: Yes, I'll handle it, should be done by Thursday.
Alice: Perfect. Carol, what's the status on payment integration?
Carol: We hit a blocker — the Stripe sandbox is down, we can't test. It could break the release.
Alice: That's a critical risk. We decided to remove dark mode from v1 scope.
Bob: Agreed.
Alice: Carol, follow up with Stripe support today.
Carol: Will do."""


@pytest.fixture
def mock_extraction():
    """
    MeetingExtraction that matches schema.
    Risks are nested inside action items and decisions — not flat.
    """

    return MeetingExtraction(
        summary="Team reviewed tasks and identified a Stripe blocker. Dark mode was cut from v1.",
        action_items=[
            ActionItem(
                description="Finish the login page",
                owner="Bob",
                due_date="Thursday",
                priority="high",
                risks=[]
            ),
            ActionItem(
                description="Follow up with Stripe support",
                owner="Carol",
                due_date="today",
                priority="high",
                risks=[
                    Risk(
                        description="Stripe sandbox still down, may block release",
                        related_to="action: Follow up with Stripe support",
                        severity="high"
                    )
                ]
            ),
        ],
        decisions=[
            Decision(
                description="Remove dark mode from v1 scope",
                made_by="Alice",
                risks=[]
            )
        ],
        general_risks=[
            Risk(
                description="Stripe API sandbox is down, blocking payment integration testing",
                related_to="general",
                severity="high"
            )
        ],
        participants=["Alice", "Bob", "Carol"]
    )