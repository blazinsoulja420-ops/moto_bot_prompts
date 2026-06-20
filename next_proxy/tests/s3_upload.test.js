const express = require('express');
const bodyParser = require('body-parser');
const request = require('supertest');
const nock = require('nock');

// Mock AWS SDK client and presigner
jest.mock('@aws-sdk/client-s3', () => {
  return {
    S3Client: function () {
      this.send = jest.fn().mockResolvedValue({});
    },
    PutObjectCommand: function PutObjectCommand() {},
    GetObjectCommand: function GetObjectCommand() {},
  };
});
jest.mock('@aws-sdk/s3-request-presigner', () => ({
  getSignedUrl: jest.fn().mockResolvedValue('https://signed.example/file.wav'),
}));

const handler = require('../pages/api/suno/generate.js');
const rateLimiter = require('../lib/rateLimiter');

describe('S3 upload integration', () => {
  let app;

  beforeEach(() => {
    rateLimiter.resetInMemory();
    app = express();
    app.use(bodyParser.json());
    app.post('/api/suno/generate', (req, res) => handler(req, res));
  });

  afterEach(() => {
    nock.cleanAll();
    jest.clearAllMocks();
  });

  test('uploads audio to S3 and returns signed URL', async () => {
    const fakeAudio = Buffer.from([0x52, 0x49, 0x46, 0x46]);
    const upstreamHost = 'https://suno.example';
    process.env.SUNO_API_URL = `${upstreamHost}/v1/generate`;
    process.env.SUNO_API_KEY = 'testkey';
    process.env.ADMIN_TOKEN = 'admintok';

    // enable S3 path
    process.env.S3_BUCKET = 'my-bucket';
    process.env.AWS_REGION = 'us-east-1';

    nock(upstreamHost).post('/v1/generate').reply(200, fakeAudio, { 'Content-Type': 'audio/wav' });

    const resp = await request(app)
      .post('/api/suno/generate')
      .set('x-admin-token', 'admintok')
      .send({ prompt: 's3 test' })
      .expect(200);

    expect(resp.body.ok).toBe(true);
    expect(resp.body.s3).toBeDefined();
    expect(resp.body.s3.url).toBe('https://signed.example/file.wav');
  });
});
