const { initRedis, checkRateLimit, resetInMemory } = require('../lib/rateLimiter');
const IORedisMock = require('ioredis-mock');

describe('rateLimiter in-memory fallback', () => {
  beforeEach(() => {
    resetInMemory();
    delete process.env.REDIS_URL;
  });

  test('allows requests under limit and blocks over limit', async () => {
    process.env.RATE_LIMIT_MAX = '3';
    process.env.RATE_LIMIT_WINDOW_SEC = '60';

    const key = 'test-client';
    let r;
    r = await checkRateLimit(key);
    expect(r.limited).toBe(false);
    r = await checkRateLimit(key);
    expect(r.limited).toBe(false);
    r = await checkRateLimit(key);
    expect(r.limited).toBe(false);
    r = await checkRateLimit(key);
    expect(r.limited).toBe(true);
  });
});

describe('rateLimiter with redis', () => {
  let origIORedis;
  beforeAll(() => {
    // monkeypatch ioredis with ioredis-mock for our module
    origIORedis = require.cache[require.resolve('ioredis')];
  });

  test('uses redis to count and enforce limits', async () => {
    // inject a mock redis client
    const mock = new IORedisMock();
    // initRedis uses ioredis constructor normally; but we can directly set client
    const rl = require('../lib/rateLimiter');
    // set internal client
    rl.__test_set_client && rl.__test_set_client(mock);

    process.env.RATE_LIMIT_MAX = '2';
    process.env.RATE_LIMIT_WINDOW_SEC = '60';

    const key = 'redis-client';
    let r;
    r = await rl.checkRateLimit(key);
    expect(r.limited).toBe(false);
    r = await rl.checkRateLimit(key);
    expect(r.limited).toBe(false);
    r = await rl.checkRateLimit(key);
    expect(r.limited).toBe(true);

    // cleanup
    mock.disconnect && mock.disconnect();
  });
});
