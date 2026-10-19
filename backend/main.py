from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as simulation_router
from app.database.models import Base, SessionLocal, engine
from app.database.seed_data import initialize_seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the ORM schema exists before seeding the catalog.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db_session:
        initialize_seed_database(db_session)
    yield


app = FastAPI(
    title="SeedTwin AI",
    description="Micro-climate digital twin simulation API for the seed industry",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
