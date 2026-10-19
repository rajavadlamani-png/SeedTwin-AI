# SeedTwin AI production deployment

## Required deployment configuration

Set these variables in the deployment environment (do not commit a production `.env` file):

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`: database initialization credentials.
- `DATABASE_URL`: SQLAlchemy PostgreSQL URL targeting the internal hostname `db:5432`, with credentials matching the three PostgreSQL variables. Production mode forces `sslmode=require`.
- `ALLOWED_ORIGINS`: an explicit JSON array such as `["https://your-domain.example"]`, or a comma-separated list of exact origins. Wildcard origins are rejected in production.
- `BACKEND_IMAGE`: a pinned backend image reference, preferably including an immutable commit tag.
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, and `DB_POOL_RECYCLE` are optional tuning controls.

Use a database password safe for the URL format or percent-encode reserved characters in the URL credentials. Store secrets in your cloud secret manager or deployment environment, never in Git.

## TLS certificate prerequisite

Before starting the production stack, place a valid certificate chain at `certs/fullchain.pem` and its matching private key at `certs/privkey.pem`. Keep the private key restricted to the deployment operator. The Nginx configuration redirects HTTP traffic to HTTPS and terminates TLS on port 443. The included ACME challenge location is a hook for an external certificate renewal process; certificate issuance and renewal are not automated by this stack.

## Start the production stack

From the repository root, with all required environment variables configured:

```sh
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Only Nginx publishes host ports 80 and 443. Neither PostgreSQL (5432) nor FastAPI (8000) is published to the host. The backend reaches PostgreSQL over the private Docker bridge network, and Nginx forwards requests to the backend over that network.

## GitHub Actions image publishing

The workflow validates Python backend syntax and builds the backend image on pushes to `main` and `feature/production-architecture`. Docker Hub publishing is opt-in: configure repository secrets `DOCKER_HUB_USERNAME` and `DOCKER_HUB_TOKEN`, then set the repository Actions variable `ENABLE_DOCKER_HUB_PUSH` to `true`. Without that variable, the workflow stops after validation and image build.

The workflow publishes a commit-SHA tag and `latest`. For production rollouts, prefer the immutable commit-SHA tag in `BACKEND_IMAGE`. This workflow builds and optionally publishes the image; it does not deploy to a cloud provider or provision a database, network, domain, or TLS certificate.

## Notes

- Production `DATABASE_URL` must use PostgreSQL. The application enforces `sslmode=require` and bounded SQLAlchemy connection-pool settings when `ENV=production`.
- Ensure the PostgreSQL service/managed database supports TLS. `sslmode=require` encrypts the connection but does not validate the server certificate identity; use `sslmode=verify-full` with a trusted CA for stricter certificate verification where supported.
- Configure cloud firewall rules to expose only the reverse proxy and restrict SSH/administration separately.
