import { useState } from 'react';

export default function SunoDemo() {
  const [prompt, setPrompt] = useState('Short upbeat electronic loop');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setAudioUrl(null);
    try {
      const resp = await fetch('/api/suno/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-token': token
        },
        body: JSON.stringify({ prompt })
      });
      const data = await resp.json();
      setResult(data);
      if (data.ok && data.s3 && data.s3.url) {
        setAudioUrl(data.s3.url);
      } else if (data.ok && data.base64 && data.contentType) {
        const blob = b64toBlob(data.base64, data.contentType);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
      }
    } catch (err) {
      setResult({ ok: false, error: String(err) });
    } finally {
      setLoading(false);
    }
  }

  function b64toBlob(b64Data, contentType = '', sliceSize = 512) {
    const byteCharacters = atob(b64Data);
    const byteArrays = [];

    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
      const slice = byteCharacters.slice(offset, offset + sliceSize);

      const byteNumbers = new Array(slice.length);
      for (let i = 0; i < slice.length; i++) {
        byteNumbers[i] = slice.charCodeAt(i);
      }

      const byteArray = new Uint8Array(byteNumbers);
      byteArrays.push(byteArray);
    }

    return new Blob(byteArrays, { type: contentType });
  }

  return (
    <div style={{ padding: 24, fontFamily: 'Arial' }}>
      <h1>Suno Proxy Demo</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 600 }}>
        <label>Admin Token (required)</label>
        <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="x-admin-token" />
        <label>Prompt</label>
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} />
        <button disabled={loading} type="submit">Generate</button>
      </form>

      {loading && <p>Generating...</p>}
      {result && <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>}
      {audioUrl && (
        <div>
          <h3>Playback</h3>
          <audio controls src={audioUrl} />
          <p><a href={audioUrl} target="_blank" rel="noreferrer">Open audio</a></p>
        </div>
      )}
    </div>
  );
}
