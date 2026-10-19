# SeedTwin AI

Micro-climate digital twin simulation sandbox for the seed industry.

## Repository structure

- `backend/app/database/models.py`: PostgreSQL configuration and SQLAlchemy ORM models.
- `backend/app/database/seed.py`: creates tables and inserts the demonstration variety catalog.
- `backend/app/api/v1/simulation_engine.py`: deterministic simulation calculation.
- `backend/app/api/v1/endpoints.py`: versioned FastAPI simulation routes.
- `frontend/src/screens/SandboxScreen.tsx`: Expo sandbox interface.

## Backend setup

Use Python 3.11 or newer and PostgreSQL 14 or newer.

1. Create a PostgreSQL database named `seedtwin_ai`.
2. From `backend/`, install dependencies with `pip install -r requirements.txt`.
3. Set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL, for example `postgresql+psycopg2://postgres:password@localhost:5432/seedtwin_ai`.
4. Run `python -m app.database.seed` from `backend/` to create the tables and insert the demonstration varieties.
5. Run `uvicorn main:app --reload --host 0.0.0.0 --port 8000` from `backend/`.

The API documentation is available at `/docs`. The simulation endpoint is `POST /api/v1/simulate-twin`.

## Frontend setup

From `frontend/`, install packages with `npm install`. Set `EXPO_PUBLIC_API_URL` in a local `.env` file to the reachable backend origin, such as `http://192.168.1.10:8000` for a phone on the same LAN. Then run `npx expo start`.

Do not use a loopback address for a physical phone: `127.0.0.1` refers to the phone itself. Configure HTTPS and a production API origin before deployment.

## Modeling boundary

The simulation implements the requested additive loss model with a 90% loss cap. Its coefficients are illustrative assumptions and must be calibrated against validated field data before agronomic or commercial decisions. The fixed 28°C reference means the supplied cold-shock rule does not activate for the demonstration varieties and a ±5°C slider; this is preserved as specified rather than silently changing the model.
