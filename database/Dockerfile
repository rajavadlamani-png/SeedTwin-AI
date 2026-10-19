FROM postgres:15-alpine

# The production Compose command creates a private self-signed PostgreSQL
# certificate on first startup. Keep OpenSSL available in the runtime image.
RUN apk add --no-cache openssl
