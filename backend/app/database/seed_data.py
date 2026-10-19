from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import SeedVariety


SEED_VARIETIES = [
    {
        "crop_name": "DroughtGuard Corn (Hybrid-C1)",
        "base_yield_kg_per_acre": Decimal("4200.00"),
        "min_temp_c": Decimal("10.00"),
        "max_temp_c": Decimal("35.00"),
        "min_germination_temp_c": Decimal("10.00"),
        "heat_resilience_factor": Decimal("0.70"),
        "drought_resilience_factor": Decimal("0.90"),
        "disease_resistance_factor": Decimal("0.55"),
        "pest_resistance_factor": Decimal("0.60"),
    },
    {
        "crop_name": "Bt-Max Cotton (Hybrid-CT4)",
        "base_yield_kg_per_acre": Decimal("1200.00"),
        "min_temp_c": Decimal("15.00"),
        "max_temp_c": Decimal("42.00"),
        "min_germination_temp_c": Decimal("15.00"),
        "heat_resilience_factor": Decimal("0.60"),
        "drought_resilience_factor": Decimal("0.50"),
        "disease_resistance_factor": Decimal("0.65"),
        "pest_resistance_factor": Decimal("0.95"),
    },
    {
        "crop_name": "Tropical-Rice (Hybrid-R9)",
        "base_yield_kg_per_acre": Decimal("2800.00"),
        "min_temp_c": Decimal("18.00"),
        "max_temp_c": Decimal("38.00"),
        "min_germination_temp_c": Decimal("18.00"),
        "heat_resilience_factor": Decimal("0.80"),
        "drought_resilience_factor": Decimal("0.30"),
        "disease_resistance_factor": Decimal("0.85"),
        "pest_resistance_factor": Decimal("0.70"),
    },
    {
        "crop_name": "Standard Wheat (Variety-W2)",
        "base_yield_kg_per_acre": Decimal("1800.00"),
        "min_temp_c": Decimal("4.00"),
        "max_temp_c": Decimal("30.00"),
        "min_germination_temp_c": Decimal("4.00"),
        "heat_resilience_factor": Decimal("0.40"),
        "drought_resilience_factor": Decimal("0.60"),
        "disease_resistance_factor": Decimal("0.60"),
        "pest_resistance_factor": Decimal("0.50"),
    },
]


def initialize_seed_database(db_session: Session) -> None:
    """Populate the variety catalog only when the table is empty."""
    existing_id = db_session.scalar(select(SeedVariety.id).limit(1))
    if existing_id is not None:
        return

    try:
        db_session.add_all(SeedVariety(**item) for item in SEED_VARIETIES)
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
