from pydantic import BaseModel, ConfigDict, Field


class AdvancedSimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_name: str = Field(min_length=1, max_length=160)
    temp_slider_shift: float = Field(ge=-5.0, le=5.0)
    water_slider_pct: float = Field(ge=-50.0, le=50.0)
    pest_pressure_pct: float = Field(ge=0.0, le=100.0)
    disease_pressure_pct: float = Field(ge=0.0, le=100.0)
    base_germination_rate: float = Field(ge=0.0, le=100.0)


class DailyHealthPoint(BaseModel):
    lifecycle_day: int
    milestone: str
    health_percentage: float = Field(ge=0.0, le=100.0)


class WeatherSummary(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    average_max_temperature_c: float
    total_precipitation_mm: float = Field(ge=0.0)
    days_included: int = Field(ge=1)
    daily_dates: list[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    crop_name: str
    final_yield_kg_per_acre: float
    calculated_loss_percentage: float
    dominant_risk_factor: str
    simulation_run_id: int
    daily_health_history: list[DailyHealthPoint]
    temp_slider_shift: float = Field(ge=-5.0, le=5.0)
    water_slider_pct: float = Field(ge=-50.0, le=50.0)
    weather_summary: WeatherSummary | None = None


class CropCatalogItem(BaseModel):
    id: int
    crop_name: str
    hybrid_code: str
    base_yield_kg_per_acre: float
    min_temp_c: float
    max_temp_c: float
    heat_resilience_factor: float
    drought_resilience_factor: float
    disease_resistance_factor: float
    pest_resistance_factor: float
