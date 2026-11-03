import { JobDetail } from '../api';

interface Props {
  job: JobDetail;
}

/** Result cards + transcript + export buttons — shown when the job completes. */
export default function Results({ job }: Props) {
  const r = job.result;
  if (!r) return null;

  const cards = [
    { title: 'Title', body: r.title },
    { title: 'Summary', body: r.summary },
    { title: 'Action Items', body: r.action_items },
    { title: 'Key Decisions', body: r.key_decisions },
    { title: 'Open Questions', body: r.questions },
  ];

  return (
    <section className="results">
      <div className="results-head">
        <h2>Results</h2>
        <div className="exports">
          <a href={`/api/export/${job.job_id}/pdf`} download>PDF</a>
          <a href={`/api/export/${job.job_id}/markdown`} download>Markdown</a>
          <a href={`/api/export/${job.job_id}/txt`} download>Transcript .txt</a>
        </div>
      </div>

      <div className="grid">
        {cards.map((c) => (
          <article key={c.title} className="card">
            <h3>{c.title}</h3>
            <pre className="card-body">{c.body || '—'}</pre>
          </article>
        ))}
      </div>

      <details className="transcript">
        <summary>Full Transcript ({r.transcript.length.toLocaleString()} chars)</summary>
        <pre>{r.transcript}</pre>
      </details>
    </section>
  );
}
