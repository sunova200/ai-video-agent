import { useEffect, useRef, useState } from 'react';
import { api, ChatMessage } from '../api';

interface Props {
  jobId: string;
  active: boolean; // job completed → chat enabled
}

export default function ChatPanel({ jobId, active }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    setError(null);
    if (active) {
      api.chatHistory(jobId).then(setMessages).catch(() => undefined);
    }
  }, [jobId, active]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  async function send() {
    const q = question.trim();
    if (!q || thinking) return;
    setQuestion('');
    setError(null);
    setMessages((m) => [...m, { role: 'user', content: q, ts: new Date().toISOString() }]);
    setThinking(true);
    try {
      const { answer } = await api.chat(jobId, q);
      setMessages((m) => [...m, { role: 'assistant', content: answer, ts: new Date().toISOString() }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setThinking(false);
    }
  }

  return (
    <section className="panel chat">
      <h2>Ask the Video</h2>
      {!active ? (
        <p className="hint">Chat unlocks when the analysis completes.</p>
      ) : (
        <>
          <div className="chat-log">
            {messages.map((m, i) => (
              <div key={i} className={`msg msg-${m.role}`}>
                <b>{m.role === 'user' ? 'You' : 'AI'}</b>
                <p>{m.content}</p>
              </div>
            ))}
            {thinking && <div className="msg msg-assistant"><b>AI</b><p className="typing">thinking…</p></div>}
            <div ref={bottomRef} />
          </div>
          <div className="chat-input">
            <input
              value={question}
              placeholder="What were the key decisions?"
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              disabled={thinking}
            />
            <button onClick={send} disabled={thinking || !question.trim()}>Send</button>
          </div>
          {error && <p className="error">{error}</p>}
        </>
      )}
    </section>
  );
}
