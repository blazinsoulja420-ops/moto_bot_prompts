const express = require('express');
const bodyParser = require('body-parser');
const request = require('supertest');
const nock = require('nock');

const handler = require('../pages/api/suno/generate.js');
const rateLimiter = require('../lib/rateLimiter');

describe('API integration /api/suno/generate', () => {
  let app;

  beforeEach(() => {
    // clear env and rate limiter
    delete process.env.SUNO_API_URL;
    delete process.env.SUNO_API_KEY;
    delete process.env.SUNO_COOKIE;
    delete process.env.S3_BUCKET;
    rateLimiter.resetInMemory();

    app = express();
    app.use(bodyParser.json());
    // mount handler on express route
    app.post('/api/suno/generate', (req, res) => {
      // Next.js handler expects (req,res) with body parsed
      return handler(req, res);
    });
  });

  afterEach(() => {
    nock.cleanAll();
  });

  test('forwards prompt to Suno and returns base64 audio when S3 not configured', async () => {
    const fakeAudio = Buffer.from([0x52, 0x49, 0x46, 0x46]); // 'RIFF' header sample
    const upstreamHost = 'https://suno.example';
    process.env.SUNO_API_URL = `${upstreamHost}/v1/generate`;
    process.env.SUNO_API_KEY = 'testkey';
    process.env.ADMIN_TOKEN = 'admintok';

    // intercept upstream and return binary audio
    nock(upstreamHost)
      .post('/v1/generate')
      .reply(200, fakeAudio, { 'Content-Type': 'audio/wav' });

    const resp = await request(app)
      .post('/api/suno/generate')
      .set('x-admin-token', 'admintok')
      .send({ prompt: 'test loop' })
      .expect(200);

    expect(resp.body.ok).toBe(true);
    expect(resp.body.contentType).toBe('audio/wav');
    expect(resp.body.base64).toBeDefined();
  });

  test('returns 401 when invalid admin token', async () => {
    process.env.SUNO_API_URL = 'https://suno.example/v1/generate';
    process.env.SUNO_API_KEY = 'testkey';
    process.env.ADMIN_TOKEN = 'admintok';

    const resp = await request(app)
      .post('/api/suno/generate')
      .set('x-admin-token', 'wrong')
      .send({ prompt: 'x' })
      .expect(401);

    expect(resp.body.ok).toBe(false);
    expect(resp.body.error).toBe('unauthorized');
  });
});
