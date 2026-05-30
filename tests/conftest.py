import pytest
import pytest_asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db

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
    return "Alice: Bob can you finish the login page by Friday?\nBob: Yes I will handle it, done by Thursday.\nAlice: Carol follow up with Stripe support today, it is blocking the release.\nCarol: Will do, the Stripe sandbox being down is a critical risk."


@pytest.fixture
def bracketed_transcript():
    return "[00:00] Alice: Good morning everyone.\n[00:05] Bob: I will finish the login page by Friday.\n[00:10] Alice: Great. We decided to use PostgreSQL."


@pytest.fixture
def speaker_label_transcript():
    return "SPEAKER_01: We need to deploy by Friday.\nSPEAKER_02: I will handle the deployment.\nSPEAKER_01: Make sure to back up the database first."


@pytest.fixture
def mock_extraction():
    from app.schemas.meeting import MeetingExtraction, ActionItem, Decision, Risk
    return MeetingExtraction(
        summary="Team reviewed sprint tasks and identified a Stripe blocker.",
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
                        description="Stripe sandbox down, blocking release",
                        related_to="action: Follow up with Stripe support",
                        severity="high"
                    )
                ]
            ),
        ],
        decisions=[
            Decision(
                description="Use PostgreSQL for the database",
                made_by="Alice",
                risks=[]
            )
        ],
        general_risks=[
            Risk(
                description="Stripe API sandbox is down",
                related_to="general",
                severity="high"
            )
        ],
        participants=["Alice", "Bob", "Carol"]
    )


@pytest.fixture
def mock_agent_report():
    return {
        "executive_summary": "Sprint planning identified two action items with a critical Stripe blocker.",
        "key_findings": ["Bob committed to Thursday deadline", "Stripe sandbox is a critical blocker"],
        "historical_context": "No relevant history found",
        "overall_risk_level": "high",
        "recommended_actions": ["Carol to contact Stripe support today"],
        "follow_up_required": True
    }


def make_mock_voyage_embedding(size: int = 1024) -> list[float]:
    # voyage-3 produces 1024-dimensional vectors by default
    return [0.1] * size


def make_mock_qdrant_results(n: int = 2) -> list:
    results = []
    for i in range(n):
        point = MagicMock()
        point.payload = {
            "meeting_id": f"meeting-{i}",
            "chunk_index": i,
            "content": f"Alice: This is chunk {i} about Stripe payments."
        }
        point.score = 0.95 - (i * 0.05)
        results.append(point)
    return results