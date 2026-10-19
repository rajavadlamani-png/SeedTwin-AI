import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    AdvancedSimulationInput,
    CropCatalogItem,
    SimulationResult,
    WeatherSummary,
)
from app.api.v1.simulation_engine import (
    fetch_real_world_weather,
    run_resilient_twin_simulation,
)
from app.database.models import SeedVariety, SimulationRun, get_db


router = APIRouter(tags=["simulation"])


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return round(min(max(value, minimum), maximum), 1)


@router.post("/simulate-twin", response_model=SimulationResult)
def simulate_twin(
    data: AdvancedSimulationInput,
    lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    lon: float | None = Query(default=None, ge=-180.0, le=180.0),
    db: Session = Depends(get_db),
) -> SimulationResult:
    if (lat is None) != (lon is None):
        raise HTTPException(
            status_code=422,
            detail="Provide both lat and lon to sync field weather.",
        )

    weather_summary: WeatherSummary | None = None
    effective_data = data
    if lat is not None and lon is not None:
        try:
            weather = fetch_real_world_weather(lat, lon)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        # Map the seven-day local climate into the existing bounded sandbox
        # controls. Temperature is relative to the engine's 28°C reference.
        # Rainfall uses 35 mm / 7 days as a neutral reference; this is a
        # transparent heuristic, not a crop-specific evapotranspiration model.
        temperature_shift = _clamp(
            float(weather["average_max_temperature_c"]) - 28.0, -5.0, 5.0
        )
        precipitation_mm = float(weather["total_precipitation_mm"])
        water_variance = _clamp(((precipitation_mm / 35.0) - 1.0) * 50.0, -50.0, 50.0)
        effective_data = data.model_copy(
            update={
                "temp_slider_shift": temperature_shift,
                "water_slider_pct": water_variance,
            }
        )
        weather_summary = WeatherSummary(**weather)

    variety = db.scalar(select(SeedVariety).where(SeedVariety.crop_name == effective_data.crop_name))
    if variety is None:
        raise HTTPException(status_code=404, detail=f"Unknown crop variety: {effective_data.crop_name}")

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

    result = run_resilient_twin_simulation(effective_data, traits)
    run = SimulationRun(
        seed_variety_id=variety.id,
        temp_slider_shift=Decimal(str(effective_data.temp_slider_shift)),
        water_slider_pct=Decimal(str(effective_data.water_slider_pct)),
        pest_pressure_pct=Decimal(str(effective_data.pest_pressure_pct)),
        disease_pressure_pct=Decimal(str(effective_data.disease_pressure_pct)),
        base_germination_rate=Decimal(str(effective_data.base_germination_rate)),
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
        daily_health_history=result["daily_health_history"],
        temp_slider_shift=float(effective_data.temp_slider_shift),
        water_slider_pct=float(effective_data.water_slider_pct),
        weather_summary=weather_summary,
    )


@router.get("/crops", response_model=list[CropCatalogItem])
def list_crops(db: Session = Depends(get_db)) -> list[CropCatalogItem]:
    """Return database-backed crop profiles for the mobile selector."""
    varieties = db.scalars(select(SeedVariety).order_by(SeedVariety.id)).all()
    catalog: list[CropCatalogItem] = []
    for variety in varieties:
        match = re.search(r"\(([^()]+)\)\s*$", variety.crop_name)
        hybrid_code = match.group(1) if match else variety.crop_name
        catalog.append(
            CropCatalogItem(
                id=variety.id,
                crop_name=variety.crop_name,
                hybrid_code=hybrid_code,
                base_yield_kg_per_acre=float(variety.base_yield_kg_per_acre),
                min_temp_c=float(variety.min_temp_c),
                max_temp_c=float(variety.max_temp_c),
                heat_resilience_factor=float(variety.heat_resilience_factor),
                drought_resilience_factor=float(variety.drought_resilience_factor),
                disease_resistance_factor=float(variety.disease_resistance_factor),
                pest_resistance_factor=float(variety.pest_resistance_factor),
            )
        )
    return catalog
