from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas import AdvancedSimulationInput, SimulationResult
from app.api.v1.simulation_engine import run_resilient_twin_simulation
from app.database.models import SeedVariety, SimulationRun, get_db


router = APIRouter(tags=["simulation"])


@router.post("/simulate-twin", response_model=SimulationResult)
def simulate_twin(
    data: AdvancedSimulationInput,
    db: Session = Depends(get_db),
) -> SimulationResult:
    variety = db.scalar(select(SeedVariety).where(SeedVariety.crop_name == data.crop_name))
    if variety is None:
        raise HTTPException(status_code=404, detail=f"Unknown crop variety: {data.crop_name}")

    traits = {
        "base_yield_kg_per_acre": variety.base_yield_kg_per_acre,
        "min_temp": variety.min_temp_c,
        "max_temp": variety.max_temp_c,
        "min_germination_temp_c": variety.min_germination_temp_c,
        "heat_resilience_factor": variety.heat_resilience_factor,
        "drought_resilience_factor": variety.drought_resilience_factor,
        "disease_resistance_factor": variety.disease_resistance_factor,
        "pest_resistance_factor": variety.pest_resistance_factor,
    }

    result = run_resilient_twin_simulation(data, traits)
    run = SimulationRun(
        seed_variety_id=variety.id,
        temp_slider_shift=Decimal(str(data.temp_slider_shift)),
        water_slider_pct=Decimal(str(data.water_slider_pct)),
        pest_pressure_pct=Decimal(str(data.pest_pressure_pct)),
        disease_pressure_pct=Decimal(str(data.disease_pressure_pct)),
        base_germination_rate=Decimal(str(data.base_germination_rate)),
        final_yield_kg_per_acre=Decimal(str(result["final_yield_kg_per_acre"])),
        calculated_loss_percentage=Decimal(str(result["calculated_loss_percentage"])),
        dominant_risk_factor=str(result["dominant_risk_factor"]),
    )

    try:
        db.add(run)
        db.commit()
        db.refresh(run)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The simulation was calculated but could not be saved.",
        ) from exc

    return SimulationResult(
        crop_name=variety.crop_name,
        final_yield_kg_per_acre=float(result["final_yield_kg_per_acre"]),
        calculated_loss_percentage=float(result["calculated_loss_percentage"]),
        dominant_risk_factor=str(result["dominant_risk_factor"]),
        simulation_run_id=run.id,
    )
