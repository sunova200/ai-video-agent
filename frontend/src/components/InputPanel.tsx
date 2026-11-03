import { FormEvent, useRef, useState } from 'react';
import { api } from '../api';

const LANGUAGES = ['english', 'hinglish', 'hindi', 'tamil', 'telugu'];

interface Props {
  onJobStarted: (jobId: string) => void;
}

export default function InputPanel({ onJobStarted }: Props) {
  const [url, setUrl] = useState('');
  const [language, setLanguage] = useState('english');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function submitUrl(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const { job_id } = await api.analyzeUrl(url.trim(), language);
      setUrl('');
      onJobStarted(job_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const { job_id } = await api.uploadFile(file, language);
      onJobStarted(job_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  return (
    <section className="panel input-panel">
      <h2>New Analysis</h2>
      <form onSubmit={submitUrl} className="url-form">
        <input
          type="url"
          placeholder="Paste a YouTube / video URL…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={busy}
        />
        <select value={language} onChange={(e) => setLanguage(e.target.value)} disabled={busy}>
          {LANGUAGES.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <button type="submit" disabled={busy || !url.trim()}>
          {busy ? 'Working…' : 'Analyze URL'}
        </button>
      </form>

      <div className="divider"><span>or</span></div>

      <label className="drop-zone">
        <input
          ref={fileRef}
          type="file"
          accept="video/*,audio/*"
          disabled={busy}
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <span>{busy ? 'Uploading…' : 'Drop / choose a video or audio file'}</span>
      </label>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
