import { useEffect, useRef, useState } from 'react';
import { api, JobDetail } from './api';

/** Polls GET /api/jobs/{id} every `intervalMs` while the job is queued/running. */
export function useJobPoller(jobId: string | null, intervalMs = 2000): JobDetail | null {
  const [job, setJob] = useState<JobDetail | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    if (!jobId) {
      setJob(null);
      return;
    }
    let cancelled = false;

    async function tick() {
      try {
        const detail = await api.getJob(jobId!);
        if (cancelled) return;
        setJob(detail);
        if (detail.status === 'queued' || detail.status === 'running') {
          timer.current = window.setTimeout(tick, intervalMs);
        }
      } catch (e) {
        if (!cancelled) console.error('poll failed', e);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [jobId, intervalMs]);

  return job;
}
