# Setu home-practice enhancement

Built against `main` commit `5e40518` on 19 November 2026. No push or deployment was made.

## What changed

- Teacher Dashboard now opens a private Parent report screen. Choose a student in your assigned class, preview the exact text, then copy it for WhatsApp. Devices that support a share sheet also get a Share button.
- Reports use up to 20 latest saved answers. They show at most two topics with missed answers and a five-minute home activity. They do not turn hand-set mastery percentages into grades or confirmed diagnoses.
- The copied note excludes the student ID and class. It has no public URL. Nothing is sent automatically. The teacher must check the recipient is an authorised parent or guardian.
- No saved answers means no invented weakness. Unsynced offline answers are not included. Reports are English only in this version.
- Ten existing English misconception bridge lessons now use bus fares, notebook bills, shop credit, same-sized rotis, lassi cups, rangoli grids, seed packets and discounts. Existing lesson IDs, concept links and misconception tags stay the same. Draft status is preserved and affected item versions increase.
- Reproducible local scripts measure a specified synthetic 3G profile and 100 simultaneous synthetic report-reading sessions. No Redis or new application dependency.

## Checks actually run

| Check | Result |
|---|---|
| Original backend suite before new tests | 131 passed |
| Complete backend suite with report tests | 142 passed, 9 existing warnings |
| Python/JavaScript engine parity | 42 of 42 checks passed |
| Frontend production build | Passed |
| New report browser test | Passed in Chrome, 390 x 844 viewport |
| Populated report in actual local app | Inspected at 390 x 844 and 1365 x 1000 |
| Clipboard contents | Checked against preview; student ID and class absent |
| Report student switching and back button | Passed |

The populated screenshots use eight synthetic answers, not real children. The report showed 3 correct answers, a roti activity and a discount activity. The report itself had no horizontal overflow at the tested sizes. The existing mobile navigation strip is scrollable, unchanged by this patch.

Not run: the entire legacy browser test suite, deployed Render/Neon checks, a real WhatsApp delivery, a school pilot, human content review, or verification on every phone/browser/theme. No improvement in learning or contest-winning probability has been established.

## Measured synthetic 3G result

Local Vite production preview, Chromium 156.0.8078.4, 390 x 844 viewport. Cold HTTP cache on each of three runs; service worker blocked to separate the initial screen from PWA background installation. Profile: 750 kbit/s download, 250 kbit/s upload, 100 ms latency, no CPU throttling. Local API demo mode was enabled.

| Run | Navigation visible | Load event | First contentful paint | Transfer bytes |
|---|---:|---:|---:|---:|
| 1 | 1,304 ms | 1,222 ms | 448 ms | 95,236 |
| 2 | 1,275 ms | 1,221 ms | 412 ms | 95,236 |
| 3 | 1,264 ms | 1,221 ms | 428 ms | 95,236 |

Each run recorded five resources: compressed response bodies totalled 93,736 bytes; decoded response bodies totalled 337,515 bytes. Transfer size also includes browser-accounted HTTP overhead. No failed requests occurred.

Safe pitch wording: "In a local lab test at 750 kbit/s download and 100 ms latency, Setu's initial navigation appeared in 1.26-1.30 seconds across three cold-cache runs."

Do not say "Setu loads in 1.3 seconds in rural India." This was local preview with compression, not a real cellular network, a lesson download, a completed diagnosis, the complete PWA cache, or a Render cold start. Deployed compression and internet latency can differ.

## Measured 100-session result

100 simultaneous synthetic sessions, each associated with one of 100 synthetic students with 20 saved answers. Every client made five sequential authenticated report requests, 500 requests total. All sessions used the same authorised synthetic teacher account, with distinct tokens. Login hashing was outside the timed section.

One local Uvicorn worker, SQLite, Python 3.11.18, Linux x86-64, two logical CPUs:

| Metric | Result |
|---|---:|
| Requests with errors | 0 / 500 |
| Median response | 211.46 ms |
| 95th percentile | 277.32 ms |
| 99th percentile | 310.48 ms |
| Timed run | 1.182 seconds |
| Throughput | 423.05 requests/second |

Safe pitch wording: "A local synthetic test of the parent-report read endpoint completed 500 authenticated requests from 100 simultaneous sessions with zero errors and a 277 ms p95 response time."

This is not proof of capacity for 100 live learners, classroom answer writes, offline sync, Render, Neon or a whole school. Those workloads need separate tests.

The first implementation used generator-scoped database dependencies and showed severe connection-pool/worker contention at this concurrency: 494 of 500 requests failed the five-second deadline. The final report endpoints keep authentication, reads and connection release together inside one worker, after which the above run passed. Existing endpoints were not rewritten. Do not extend this result to their concurrency behaviour.

Raw measurements are included in `docs/setu-3g-results.json` and `docs/setu-report-load-results.json` in the patch.

## Repeat the measurements locally

From the repository root, with the Python environment already activated:

```powershell
python scripts/benchmark_parent_reports.py
```

This script creates its own temporary database and local server, uses synthetic records, and removes them afterwards. It does not contact Render. Tokens are kept in memory and not printed.

For the 3G script, first build the frontend. Start the local API in one terminal, with your normal local demo configuration. In another terminal:

```powershell
cd frontend
npm run preview -- --host 127.0.0.1 --port 4173
```

In a third terminal from the repository root:

```powershell
cd frontend
npx playwright install chromium
node scripts/benchmark_3g.mjs http://127.0.0.1:4173
```

The landing page requests demo profiles. Enable local demo mode if that request is otherwise refused; do not alter a deployed environment for this test. The script rejects non-local URLs. The chosen speed profile is stated explicitly instead of treating "3G" as one universal speed.
