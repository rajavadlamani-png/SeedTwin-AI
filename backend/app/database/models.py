import os
from datetime import datetime
from decimal import Decimal
from typing import Generator

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, create_engine, func
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker



def _database_configuration() -> tuple[str, dict[str, int | bool]]:
    raw_database_url = os.getenv("DATABASE_URL")
    if not raw_database_url:
        raise RuntimeError(
            "DATABASE_URL must be configured explicitly; no default credentials are provided."
        )

    is_production = os.getenv("ENV", "development").strip().lower() == "production"
    engine_options: dict[str, int | bool] = {"pool_pre_ping": True}

    if is_production:
        try:
            parsed_url = make_url(raw_database_url)
        except Exception as exc:
            raise RuntimeError("DATABASE_URL is not a valid SQLAlchemy URL.") from exc

        if parsed_url.get_backend_name() != "postgresql":
            raise RuntimeError("Production DATABASE_URL must use PostgreSQL.")

        # Enforce TLS regardless of whether a caller supplied an SSL query option.
        secure_query = dict(parsed_url.query)
        secure_query["sslmode"] = "require"
        raw_database_url = parsed_url.set(query=secure_query).render_as_string(
            hide_password=False
        )
        engine_options.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            }
        )

    return raw_database_url, engine_options


DATABASE_URL, _ENGINE_OPTIONS = _database_configuration()
engine: Engine = create_engine(DATABASE_URL, **_ENGINE_OPTIONS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class SeedVariety(Base):
    __tablename__ = "seed_varieties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    crop_name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    base_yield_kg_per_acre: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_temp_c: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_temp_c: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    min_germination_temp_c: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    heat_resilience_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.50"), server_default="0.50"
    )
    drought_resilience_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.50"), server_default="0.50"
    )
    disease_resistance_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.50"), server_default="0.50"
    )
    pest_resistance_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.50"), server_default="0.50"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        back_populates="seed_variety",
        cascade="all, delete-orphan",
    )


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seed_variety_id: Mapped[int] = mapped_column(
        ForeignKey("seed_varieties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    temp_slider_shift: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    water_slider_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    pest_pressure_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    disease_pressure_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    base_germination_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    final_yield_kg_per_acre: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    calculated_loss_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    dominant_risk_factor: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    seed_variety: Mapped[SeedVariety] = relationship(back_populates="simulation_runs")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
