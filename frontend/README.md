# SeedTwin AI — Mobile Frontend

React Native + Expo mobile interface for the SeedTwin AI digital-twin simulation API.

## Configure the API URL

1. Copy `.env.example` to a local file named `.env` in the `frontend/` directory.
2. Keep `http://localhost:8000` when running the app in a browser/simulator where localhost reaches the backend.
3. When using Expo Go on a physical iOS or Android device, replace `localhost` with your development computer's local Wi-Fi/LAN IP address. For example:

   ```env
   EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
   ```

   Replace `192.168.1.10` with your computer's actual local IP. Ensure the phone and computer are on the same Wi-Fi network and that the computer firewall permits inbound connections to port `8000`.

4. Start the API from the repository root with `docker compose up --build`, then start Expo from `frontend/`:

   ```bash
   npm install
   npx expo start
   ```

Expo public environment variables are bundled into the app. Do not put secrets in `EXPO_PUBLIC_*` variables.

## Dashboard visualizations and field weather

- The lifecycle health line chart plots the backend's `daily_health_history` at Sowing, Vegetative, Flowering, and Maturity. It is a scenario projection, not observed field telemetry. The line is green above 80% final health, orange from 50% through 80%, and red below 50%.
- Use **Sync Local Field Weather** to enter latitude and longitude. The app sends them as `lat` and `lon` query parameters to `POST /api/v1/simulate-twin`.
- The backend calls the unauthenticated Open-Meteo forecast API with a timeout, averages available daily maximum temperatures, and sums daily precipitation over the returned past-week window.
- The temperature baseline maps average maximum temperature against 28°C and is clamped to the existing -5°C to +5°C slider range. Rainfall maps against a 35 mm reference over the requested window and is clamped to the existing -50% to +50% water-variance range. These are transparent sandbox heuristics, not agronomic irrigation or evapotranspiration recommendations.
- The API response returns the effective slider values and a weather summary, which the app uses to synchronize its controls and show the fetched climate values.

## Database-backed workflow

- `GET /api/v1/crops` loads the current seeded crop catalog and its resilience coefficients.
- `POST /api/v1/simulate-twin` runs a simulation for the selected `crop_name` and the five slider inputs. Supplying both `lat` and `lon` overrides the temperature and water controls with the weather-derived baseline.
- The backend stores successful simulation runs in PostgreSQL.
