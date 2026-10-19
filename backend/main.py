import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as simulation_router
from app.database.models import Base, SessionLocal, engine
from app.database.seed_data import initialize_seed_database


def _allowed_origins() -> list[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    is_production = os.getenv("ENV", "development").strip().lower() == "production"

    if raw_origins:
        try:
            decoded = json.loads(raw_origins)
        except json.JSONDecodeError:
            # Also support a comma-separated list for straightforward container envs.
            decoded = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

        if not isinstance(decoded, list) or any(
            not isinstance(origin, str) or not origin.strip() for origin in decoded
        ):
            raise RuntimeError(
                "ALLOWED_ORIGINS must be a JSON array or comma-separated list of origins."
            )
        origins = [origin.strip().rstrip("/") for origin in decoded]
    elif is_production:
        raise RuntimeError("ALLOWED_ORIGINS must be set explicitly in production.")
    else:
        origins = [
            "http://localhost:19006",
            "http://localhost:8081",
            "http://127.0.0.1:8081",
        ]

    if is_production and ("*" in origins or not origins):
        raise RuntimeError(
            "Production ALLOWED_ORIGINS must contain explicit origins and cannot include '*'."
        )
    return origins


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
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
)

app.include_router(simulation_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
