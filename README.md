# SeedTwin AI

Micro-climate digital twin simulation sandbox for the seed industry.

## Repository structure

- `backend/app/database/models.py`: PostgreSQL configuration and SQLAlchemy ORM models.
- `backend/app/database/seed_data.py`: seeds the four-variety catalog on API startup when the table is empty.
- `backend/app/api/v1/simulation_engine.py`: deterministic simulation calculation.
- `backend/app/api/v1/endpoints.py`: versioned FastAPI simulation routes.
- `frontend/src/screens/SandboxScreen.tsx`: Expo sandbox interface.
- `docker-compose.yml`: PostgreSQL and FastAPI local deployment.

## Run with Docker Compose

From the repository root, run:

```bash
docker compose up --build
```

Compose starts PostgreSQL 15 and waits for its health check before starting FastAPI. The backend connects to `postgresql://seed_admin:seed_secure_pass@db:5432/seed_twin_db`; the database is persisted in the `seed_twin_postgres_data` volume. On first startup, the API creates the ORM tables and seeds the four requested varieties if `seed_varieties` is empty.

- API: http://localhost:8000
- OpenAPI documentation: http://localhost:8000/docs
- Health endpoint: http://localhost:8000/health

The PostgreSQL port is exposed on `localhost:5432` for local database tools. The compose credentials are intended for local development; replace them with managed secrets before deploying to a shared or public environment.

## Run the backend without Docker

Use Python 3.11 or newer and PostgreSQL 14 or newer.

1. Create a PostgreSQL database named `seed_twin_db` with user `seed_admin` and password `seed_secure_pass`.
2. From `backend/`, install dependencies with `pip install -r requirements.txt`.
3. Set `DATABASE_URL` to `postgresql+psycopg2://seed_admin:seed_secure_pass@localhost:5432/seed_twin_db`.
4. Run `uvicorn main:app --reload --host 0.0.0.0 --port 8000` from `backend/`. Startup creates tables and seeds the catalog if empty.

The simulation endpoint is `POST /api/v1/simulate-twin`.

## Frontend setup

From `frontend/`, install packages with `npm install`. Set `EXPO_PUBLIC_API_URL` in a local `.env` file to the reachable backend origin, such as `http://192.168.1.10:8000` for a phone on the same LAN. Then run `npx expo start`.

Do not use a loopback address for a physical phone: `127.0.0.1` refers to the phone itself. Configure HTTPS and a production API origin before deployment.

## Modeling boundary

The simulation implements the requested additive loss model with a 90% loss cap. Its coefficients are illustrative assumptions and must be calibrated against validated field data before agronomic or commercial decisions. The fixed 28°C reference means the supplied cold-shock rule does not activate for the demonstration varieties and a ±5°C slider; this is preserved as specified rather than silently changing the model.
