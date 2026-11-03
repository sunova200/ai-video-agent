import { useEffect, useState } from 'react';
import { api, JobSummary } from './api';
import { useJobPoller } from './hooks';
import InputPanel from './components/InputPanel';
import StepTracker from './components/StepTracker';
import Results from './components/Results';
import ChatPanel from './components/ChatPanel';

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [history, setHistory] = useState<JobSummary[]>([]);
  const job = useJobPoller(jobId);

  useEffect(() => {
    api.listJobs().then(setHistory).catch(() => undefined);
  }, [job?.status]);

  const completed = job?.status === 'completed';

  return (
    <div className="shell">
      <header>
        <h1>AI Video Assistant</h1>
        <p className="tagline">Transcribe · Summarize · Extract · Chat with any meeting or video</p>
      </header>

      <main className="layout">
        <aside className="left">
          <InputPanel onJobStarted={setJobId} />

          <section className="panel history">
            <h2>Recent Jobs</h2>
            {history.length === 0 && <p className="hint">Nothing yet — start an analysis.</p>}
            <ul>
              {history.map((j) => (
                <li key={j.job_id}>
                  <button
                    className={`hist-item ${j.job_id === jobId ? 'active' : ''}`}
                    onClick={() => setJobId(j.job_id)}
                  >
                    <span className={`pill pill-${j.status}`}>{j.status}</span>
                    <span className="hist-title">{j.title || j.source}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section className="right">
          {!job && <div className="panel empty-state">Start an analysis to see live progress here.</div>}
          {job && (
            <>
              <StepTracker job={job} />
              {completed && <Results job={job} />}
              <ChatPanel jobId={job.job_id} active={completed} />
            </>
          )}
        </section>
      </main>
    </div>
  );
}
