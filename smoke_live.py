"""Live end-to-end smoke test against a REAL uvicorn server (ML deps stubbed)."""
import json, time, urllib.request

BASE = "http://127.0.0.1:8000"

def req(path, data=None, method=None, raw=False):
    r = urllib.request.Request(BASE + path, method=method or ("POST" if data else "GET"))
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, body) as resp:
        content = resp.read()
        return content if raw else json.loads(content)

print("health:", req("/api/health"))
job = req("/api/jobs/analyze-url", {"url": "https://youtube.com/watch?v=live_smoke", "language": "english"})
jid = job["job_id"]
print("job created:", jid)

for _ in range(50):
    d = req(f"/api/jobs/{jid}")
    if d["status"] in ("completed", "failed"):
        break
    time.sleep(0.3)
print("final status:", d["status"], "| progress:", d["progress"], "| steps:", [(s["name"], s["state"]) for s in d["steps"]])
assert d["status"] == "completed", d

ans = req(f"/api/chat/{jid}", {"question": "What was decided?"})
print("chat answer:", ans["answer"])
md = req(f"/api/export/{jid}/markdown", raw=True).decode()
print("markdown export starts:", md.splitlines()[0])
html = req("/", raw=True).decode()
assert "AI Video Assistant" in html and "/assets/" in html
print("frontend served at / : OK (React bundle linked)")
print("\nALL LIVE CHECKS PASSED ✔")
