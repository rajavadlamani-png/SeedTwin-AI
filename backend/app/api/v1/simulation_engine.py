from typing import Any

import requests

from app.api.v1.schemas import AdvancedSimulationInput


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 8


def fetch_real_world_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Fetch the previous seven days of local weather from Open-Meteo.

    Coordinates are validated by the caller's API query schema. The request is
    bounded by a timeout and raises ValueError with a safe message on failure.
    """
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("Longitude must be between -180 and 180.")

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,precipitation_sum",
                "timezone": "auto",
                "past_days": 7,
            },
            timeout=WEATHER_TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ValueError("Unable to retrieve field weather from Open-Meteo.") from exc

    daily = payload.get("daily") or {}
    temperatures = daily.get("temperature_2m_max") or []
    precipitation = daily.get("precipitation_sum") or []
    dates = daily.get("time") or []
    valid_temperatures = [
        float(value) for value in temperatures if isinstance(value, (int, float))
    ]
    valid_precipitation = [
        float(value) for value in precipitation if isinstance(value, (int, float))
    ]
    if not valid_temperatures or not valid_precipitation:
        raise ValueError("Open-Meteo returned no usable daily weather values.")

    return {
        "latitude": latitude,
        "longitude": longitude,
        "average_max_temperature_c": round(
            sum(valid_temperatures) / len(valid_temperatures), 2
        ),
        "total_precipitation_mm": round(sum(valid_precipitation), 2),
        "days_included": min(len(valid_temperatures), len(valid_precipitation)),
        "daily_dates": dates,
    }


def run_resilient_twin_simulation(
    data: AdvancedSimulationInput,
    traits: dict[str, Any],
) -> dict[str, Any]:
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
    loss_percentage = round(total_loss * 100.0, 2)

    if total_loss == 0.0:
        dominant_risk = "Optimal"
    else:
        risk_scores = {
            "Climate": climate_loss,
            "Biological": biological_loss,
            "Quality": quality_loss,
        }
        dominant_risk = max(risk_scores, key=risk_scores.get)

    # A milestone projection of the calculated scenario loss, not observed
    # field telemetry. Loss is progressively realized over the crop lifecycle.
    daily_health_history = [
        {"lifecycle_day": 1, "milestone": "Sowing", "health_percentage": round(100.0 - loss_percentage * 0.10, 2)},
        {"lifecycle_day": 25, "milestone": "Vegetative", "health_percentage": round(100.0 - loss_percentage * 0.35, 2)},
        {"lifecycle_day": 55, "milestone": "Flowering", "health_percentage": round(100.0 - loss_percentage * 0.70, 2)},
        {"lifecycle_day": 90, "milestone": "Maturity", "health_percentage": round(100.0 - loss_percentage, 2)},
    ]

    return {
        "final_yield_kg_per_acre": round(final_yield, 2),
        "calculated_loss_percentage": loss_percentage,
        "dominant_risk_factor": dominant_risk,
        "daily_health_history": daily_health_history,
    }
