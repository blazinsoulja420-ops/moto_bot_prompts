Next.js Suno Proxy

Purpose
- Lightweight Next.js API route that proxies server-side Suno audio generation requests.

Files
- pages/api/suno/generate.js — API route (server-only) that forwards POST requests to the configured Suno API URL.
- .env.example — required server env vars and defaults.
- package.json — minimal scripts to run the Next dev server.

Usage
1. Copy `.env.example` -> `.env.local` and set values (especially `ADMIN_TOKEN` and `SUNO_API_URL`).
2. Install dependencies and run dev server:

```bash
npm install
npm run dev
```

3. Call the API from a trusted server or admin client:

POST /api/suno/generate
Headers: `x-admin-token: <ADMIN_TOKEN>`
Body JSON: `{ "prompt": "...", "model": null, "voice": null }`

Response
- On success this route returns either JSON from the upstream Suno API or a base64 audio payload with `contentType`.

Notes
- This is a scaffold: set `SUNO_API_URL` to your vendor endpoint (or an internal backend endpoint) and keep `ADMIN_TOKEN` secret.
- For production consider:
  - Storing generated audio in S3 and returning a signed URL.
  - Rate-limiting, authentication, request size limits, input validation, and monitoring.
 - This scaffold supports optional S3 storage. If you set `S3_BUCKET` and AWS credentials in `.env.local`, the API route will upload generated audio to S3 and return a signed URL.
 - A minimal frontend demo is available at `/suno` which accepts an admin token and prompt for testing.

Rate limiting and validation
- Environment variables: `RATE_LIMIT_MAX` (default 5 requests) and `RATE_LIMIT_WINDOW_SEC` (default 60 seconds) control a simple in-memory rate limiter.
- The API performs basic input validation (prompt required, length limits) to protect upstream usage and costs.

Notes on limitations
- The bundled in-memory rate limiter is per-process only. For production, use a shared store (Redis) or API gateway rate limiting to cover multiple instances. Set `REDIS_URL` to enable Redis-backed rate limiting.

Metrics and logging
- A Prometheus metrics endpoint is available at `/api/metrics`. The API records request, error, rate-limit, and request-duration metrics. Configure a Prometheus scrape to collect these.
- Logging uses `pino`. Configure `LOG_LEVEL` (default `info`). Logs are emitted to stdout for easy ingestion by container logging systems.

Production checklist
- Store `ADMIN_TOKEN`, `SUNO_API_KEY`/`SUNO_COOKIE`, and AWS/Redis credentials in a secrets store (not in git).
- Use HTTPS and a stable domain for the proxy. Protect access with a firewall or auth layer.
- Consider adding:
  - Centralized rate limiting (API gateway or Redis-based limiter with request identification)
  - AuthZ (per-user quotas) and billing controls
  - Monitoring/alerts for `suno_upstream_error` rate and 5xx responses
  - S3 lifecycle rules for temporary audio files (or move to object lifecycle + signed URLs)
  - Circuit breaker / exponential backoff for upstream Suno calls
