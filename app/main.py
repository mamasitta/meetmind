from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.meetings_api_route import router as meetings_router
from app.api.agent_api_route import router as agent_router
from app.rag.qdrant_client import ensure_collection_exists



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run on start, create tables if dont exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # create qgrant collection if its doesn"t exist
    await ensure_collection_exists()
    
    yield
    # Runs on shutdown, clean up connections
    await engine.dispose()


app = FastAPI(
    title = "MeetMind API",
    description = "AI powered meeting intelegence backend",
    version = "0.1.0",
    lifespan = lifespan
)

# include meetings api router
app.include_router(meetings_router)
app.include_router(agent_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# start the server
# uvicorn app.main:app --reload