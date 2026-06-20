const promClient = require('prom-client');

// Ensure metrics are initialized in the other module; this exposes the global registry.
export default async function handler(req, res) {
  try {
    res.setHeader('Content-Type', promClient.register.contentType);
    const metrics = await promClient.register.metrics();
    res.status(200).send(metrics);
  } catch (err) {
    console.error('metrics error', err);
    res.status(500).send('error');
  }
}
