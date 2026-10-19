from typing import Any

from app.api.v1.schemas import AdvancedSimulationInput


def run_resilient_twin_simulation(
    data: AdvancedSimulationInput,
    traits: dict[str, Any],
) -> dict[str, float | str]:
    base_yield = float(traits["base_yield_kg_per_acre"])
    climate_loss = 0.0
    biological_loss = 0.0
    quality_loss = 0.0

    if data.temp_slider_shift > 0:
        raw_heat_shock = data.temp_slider_shift * 0.05
        climate_loss += raw_heat_shock * (1.0 - float(traits["heat_resilience_factor"]))

    effective_temperature = 28.0 + data.temp_slider_shift
    if effective_temperature < float(traits["min_germination_temp_c"]):
        climate_loss += 0.15

    if data.water_slider_pct < 0:
        raw_drought_shock = abs(data.water_slider_pct) * 0.01
        climate_loss += raw_drought_shock * (1.0 - float(traits["drought_resilience_factor"]))

    biological_loss += (
        data.pest_pressure_pct / 100.0
    ) * 0.30 * (1.0 - float(traits["pest_resistance_factor"]))

    biological_loss += (
        data.disease_pressure_pct / 100.0
    ) * 0.40 * (1.0 - float(traits["disease_resistance_factor"]))

    if data.base_germination_rate < 90.0:
        quality_loss = (90.0 - data.base_germination_rate) * 0.01

    total_loss = min(max(climate_loss + biological_loss + quality_loss, 0.0), 0.90)
    final_yield = max(base_yield * (1.0 - total_loss), 0.0)

    if total_loss == 0.0:
        dominant_risk = "Optimal"
    else:
        risk_scores = {
            "Climate": climate_loss,
            "Biological": biological_loss,
            "Quality": quality_loss,
        }
        dominant_risk = max(risk_scores, key=risk_scores.get)

    return {
        "final_yield_kg_per_acre": round(final_yield, 2),
        "calculated_loss_percentage": round(total_loss * 100.0, 2),
        "dominant_risk_factor": dominant_risk,
    }
