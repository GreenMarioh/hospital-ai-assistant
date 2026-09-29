# Load test

Script: `loadtest/k6.js`. Scenario: **50 concurrent virtual users** doing realistic non-AI traffic (patient portal reads, reception search/calendar, doctor schedule)
with 1-3 s think time, plus 2 logins per second. Targets: browse p95 < 300 ms, errors < 1 %.

```bash
make e2e-up                     # stack with 4 API workers, rate limiting off
k6 run -e BASE_URL=http://localhost:8000 loadtest/k6.js
k6 run -e VUS=50 -e LOGIN_RATE=0 -e DURATION=30s ...   # variations
```

## Result (4 uvicorn workers on a shared 12-thread developer machine that was also running a browser and a VM)
| Metric | Value |
|---|---|
| Browse p50 / p90 / **p95** | 20 ms / 44 ms / **67 ms** |
| Slowest endpoint p95 (`slots`) | 87 ms |
| Login p95 (argon2id, 2 logins/s) | 259 ms |
| Error rate | 0 % |
| Throughput | ~70 req/s |

## What we learned (and fixed)
1. **Connection-pool deadlock**: the audit middleware opened a second DB connection while the request still held one; at 50 concurrent requests the shared pool of 20 was exhausted and requests timed out after 30 s. Audit writes now use a separate small pool and run after the response is sent.
2. **argon2 on the event loop** blocked all requests during logins: hashing now runs in a thread pool, with the OWASP-recommended profile (19 MiB, t=2, p=1) instead of the library default (64 MiB, p=4).
3. Middleware was converted from `BaseHTTPMiddleware` to pure ASGI and the doctor list N+1 was removed.

## Limits
Offered load beyond roughly 100 req/s (50 VUs with < 1 s think time) saturated this machine and pushed p95 to ~0.6-0.9 s. That is a much heavier profile than 50 human users;
scale by raising `WEB_CONCURRENCY` and adding DB CPU. AI endpoints are excluded because latency is dominated by the LLM.
