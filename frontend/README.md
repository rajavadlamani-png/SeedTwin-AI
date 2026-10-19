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

## Database-backed workflow

- `GET /api/v1/crops` loads the current seeded crop catalog and its resilience coefficients.
- `POST /api/v1/simulate-twin` runs a simulation for the selected `crop_name` and the five slider inputs.
- The backend stores successful simulation runs in PostgreSQL.
