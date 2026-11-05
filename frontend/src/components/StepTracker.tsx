import { JobDetail } from '../api';

/** Six-dot pipeline tracker mirroring the original Streamlit step design. */
export default function StepTracker({ job }: { job: JobDetail }) {
  const pct = Math.round(job.progress * 100);
  return (
    <section className="panel tracker">
      <div className="tracker-head">
        <h2>Pipeline</h2>
        <span className="status-badge" data-status={job.status}>{job.status} · {pct}%</span>
      </div>
      <ol className="steps">
        {job.steps.map((s) => (
          <li key={s.name} className="step" data-state={s.state}>
            <span className="dot" />
            <span className="step-label">{s.label}</span>
          </li>
        ))}
      </ol>
      {job.error && <p className="error">{job.error}</p>}
    </section>
  );
}
