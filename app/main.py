from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import engine, Base



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run on start, create tables if dont exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Runs on shutdown, clean up connections
    await engine.dispose()


app = FastAPI(
    title = "MeetMind API",
    description = "AI powered meeting intelegence backend",
    version = "0.1.0",
    lifespan = lifespan
)

@app.get("/health")
async def health():
    return {"status": "ok"}
