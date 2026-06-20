// Simple in-memory rate limiter (per-process). Good for single-instance
// deployments or lightweight protection. Configure with env vars:
// RATE_LIMIT_MAX (requests) and RATE_LIMIT_WINDOW_SEC (seconds).
const rateLimits = new Map();
function checkRateLimit(key) {
  const max = parseInt(process.env.RATE_LIMIT_MAX || '5', 10);
  const windowSec = parseInt(process.env.RATE_LIMIT_WINDOW_SEC || '60', 10);
  const now = Date.now();
  const windowMs = windowSec * 1000;
  const entry = rateLimits.get(key);
  if (!entry || now - entry.start >= windowMs) {
    rateLimits.set(key, { count: 1, start: now });
    return { limited: false, remaining: max - 1, reset: now + windowMs };
  }
  if (entry.count >= max) {
    return { limited: true, remaining: 0, reset: entry.start + windowMs };
  }
  entry.count += 1;
  rateLimits.set(key, entry);
  return { limited: false, remaining: max - entry.count, reset: entry.start + windowMs };
}

// Export handler for CommonJS-based tests (Jest/express).
try {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = typeof handler !== 'undefined' ? handler : module.exports;
  }
} catch (e) {
  // ignore in ESM environments
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'method_not_allowed' });

  try {
    const adminHeader = req.headers['x-admin-token'] || req.headers['X-Admin-Token'];
    if (!process.env.ADMIN_TOKEN || adminHeader !== process.env.ADMIN_TOKEN) {
      return res.status(401).json({ ok: false, error: 'unauthorized' });
    }

      const { z } = require('zod');
      const pino = require('pino');
      const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
      const promClient = require('prom-client');

      // Prometheus metrics (safe singletons across HMR)
      if (!global.__suno_metrics_initialized) {
        const register = promClient.register;
        global.__suno_metrics = {
          requestCounter: new promClient.Counter({ name: 'suno_requests_total', help: 'Total Suno proxy requests' }),
          errorCounter: new promClient.Counter({ name: 'suno_errors_total', help: 'Total Suno proxy errors' }),
          rateLimitCounter: new promClient.Counter({ name: 'suno_rate_limited_total', help: 'Total rate limited requests' }),
          requestDuration: new promClient.Histogram({ name: 'suno_request_duration_seconds', help: 'Request durations', buckets: [0.1, 0.5, 1, 2, 5, 10] }),
          register,
        };
        global.__suno_metrics_initialized = true;
      }

      const metrics = global.__suno_metrics;

      const { checkRateLimit, initRedis, resetInMemory } = require('../../../lib/rateLimiter');

      // initialize redis client if configured
      if (process.env.REDIS_URL) {
        initRedis(process.env.REDIS_URL);
      }

      const bodySchema = z.object({
        prompt: z.string().min(1).max(20000),
        model: z.string().max(200).nullable().optional(),
        voice: z.string().max(200).nullable().optional(),
      });

      model: model || process.env.SUNO_DEFAULT_MODEL || null,
      voice: voice || process.env.SUNO_DEFAULT_VOICE || null,
    };

    const headers = { 'Content-Type': 'application/json' };
    if (process.env.SUNO_API_KEY) headers['Authorization'] = `Bearer ${process.env.SUNO_API_KEY}`;
    else if (process.env.SUNO_COOKIE) headers['Cookie'] = process.env.SUNO_COOKIE;
    else return res.status(500).json({ ok: false, error: 'missing_suno_key_or_cookie' });

    const upstream = await fetch(SUNO_API_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      // do not follow too many redirects automatically
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      return res.status(upstream.status).json({ ok: false, error: 'suno_upstream_error', status: upstream.status, body: text });
    }

    const contentType = upstream.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const json = await upstream.json();
      return res.status(200).json(json);
    }

    // Otherwise treat as binary audio. Prefer storing to S3 if configured,
    // otherwise return base64 payload for direct client playback.
    const arrayBuffer = await upstream.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const S3_BUCKET = process.env.S3_BUCKET || process.env.S3_BUCKET_NAME || process.env.AWS_S3_BUCKET;
    if (S3_BUCKET && process.env.AWS_REGION) {
      try {
        const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
        const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');

        const s3Client = new S3Client({
          region: process.env.AWS_REGION,
          credentials: process.env.AWS_ACCESS_KEY_ID
            ? { accessKeyId: process.env.AWS_ACCESS_KEY_ID, secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY }
            : undefined,
        });

        const ext = (contentType.split('/')[1] || 'bin').split(';')[0];
        const key = `suno/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;

        await s3Client.send(new PutObjectCommand({
          Bucket: S3_BUCKET,
          Key: key,
          Body: buffer,
          ContentType: contentType,
        }));

        const signedUrl = await getSignedUrl(
          s3Client,
          new GetObjectCommand({ Bucket: S3_BUCKET, Key: key }),
          { expiresIn: 60 * 60 }
        );

        return res.status(200).json({ ok: true, contentType, s3: { bucket: S3_BUCKET, key, url: signedUrl } });
      } catch (e) {
        console.error('S3 upload failed', e);
        // fallback to returning base64
      }
    }

    const base64 = buffer.toString('base64');
    return res.status(200).json({ ok: true, contentType, base64 });
  } catch (err) {
    console.error('generate.js error', err);
    return res.status(500).json({ ok: false, error: 'internal_error', message: String(err) });
  }
}
