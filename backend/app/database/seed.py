from decimal import Decimal

from sqlalchemy import select

from app.database.models import Base, SeedVariety, SessionLocal, engine


DEMO_VARIETIES = [
    {
        "crop_name": "Standard-Corn-Hybrid",
        "base_yield_kg_per_acre": Decimal("4000.00"),
        "min_temp_c": Decimal("10.00"),
        "max_temp_c": Decimal("35.00"),
        "min_germination_temp_c": Decimal("10.00"),
        "heat_resilience_factor": Decimal("0.40"),
        "drought_resilience_factor": Decimal("0.35"),
        "disease_resistance_factor": Decimal("0.50"),
        "pest_resistance_factor": Decimal("0.50"),
    },
    {
        "crop_name": "ClimateGuard-BioCorn-V2",
        "base_yield_kg_per_acre": Decimal("4350.00"),
        "min_temp_c": Decimal("9.00"),
        "max_temp_c": Decimal("38.00"),
        "min_germination_temp_c": Decimal("9.00"),
        "heat_resilience_factor": Decimal("0.85"),
        "drought_resilience_factor": Decimal("0.90"),
        "disease_resistance_factor": Decimal("0.75"),
        "pest_resistance_factor": Decimal("0.80"),
    },
]


def seed_catalog() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for variety_data in DEMO_VARIETIES:
            existing = db.scalar(
                select(SeedVariety).where(SeedVariety.crop_name == variety_data["crop_name"])
            )
            if existing is None:
                db.add(SeedVariety(**variety_data))
        db.commit()


if __name__ == "__main__":
    seed_catalog()
