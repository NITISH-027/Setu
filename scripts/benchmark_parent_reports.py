"""Local-only synthetic HTTP benchmark. Never targets the deployed site.

100 distinct synthetic students and teacher sessions, 5 report reads per user.
This is NOT a school-scale capacity claim, write-load test, or cloud benchmark.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def percentile(values, p):
    values = sorted(values)
    return round(values[max(0, min(len(values) - 1, int((len(values) - 1) * p)))], 2)


def main():
    with tempfile.TemporaryDirectory(prefix='setu_load_test_') as tmp:
        os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(tmp) / 'load_test.db')
        os.environ['SETU_DEMO_MODE'] = 'false'
        os.environ['ENV'] = 'development'
        sys.path.insert(0, str(ROOT / 'backend'))
        from app.db import init_db, SessionLocal, UserDB, StudentDB, AttemptDB
        from app.auth.security import create_session
        import requests
        print('Preparing isolated synthetic benchmark data...', file=sys.stderr, flush=True)
        init_db()
        db = SessionLocal()
        db.add(UserDB(id='bench_teacher', username='bench_teacher', password_hash='unused-not-a-login', role='teacher', assigned_classes='["bench"]'))
        tokens = []
        for i in range(100):
            sid = f'bench_{i:03}'
            db.add(StudentDB(pseudonymous_id=sid, subject_key='subject_' + sid, class_id='bench', pin_hash='unused', salt='unused'))
            for j in range(20):
                db.add(AttemptDB(id=f'{sid}_{j}', student_id=sid, question_id='synthetic', concept_id='c8_math_rational_ops', selected_option_id='synthetic', is_correct=(j % 3 != 0)))
            db.commit()
            tokens.append(create_session(db, user_id='bench_teacher', role='teacher').token)
        db.close()
        print('Synthetic data ready; starting local HTTP server...', file=sys.stderr, flush=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with open(Path(tmp) / 'server.log', 'w') as log:
            server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT / 'backend', stdout=log, stderr=log)
            try:
                for _ in range(150):
                    try:
                        if requests.get(base + '/health', timeout=1).ok:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError('Local benchmark server did not become ready.')
                print('Local HTTP server ready; starting 100 clients...', file=sys.stderr, flush=True)
                gate = threading.Barrier(100)
                def user(i):
                    timings, errors = [], 0
                    with requests.Session() as client:
                        client.headers['Authorization'] = 'Bearer ' + tokens[i]
                        gate.wait(timeout=5)
                        for _ in range(5):
                            start = time.perf_counter()
                            try:
                                response = client.get(base + f'/api/teacher/student/bench_{i:03}/parent-report', timeout=5)
                                if response.status_code != 200 or response.json().get('attempts_used') != 20:
                                    errors += 1
                            except (requests.RequestException, ValueError):
                                errors += 1
                            timings.append((time.perf_counter() - start) * 1000)
                    return timings, errors
                start = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as pool:
                    results = list(pool.map(user, range(100)))
                duration = time.perf_counter() - start
                timings = [t for result, _ in results for t in result]
                result = {'scope': 'local HTTP, one uvicorn worker, SQLite, authenticated parent-report reads only',
                          'synthetic_users': 100, 'requests': len(timings), 'errors': sum(e for _, e in results),
                          'elapsed_seconds': round(duration, 3), 'requests_per_second': round(len(timings) / duration, 2),
                          'p50_ms': percentile(timings, .50), 'p95_ms': percentile(timings, .95), 'p99_ms': percentile(timings, .99),
                          'platform': platform.platform(), 'python': platform.python_version(), 'logical_cpus': os.cpu_count(),
                          'generated_at_utc': datetime.utcnow().isoformat() + 'Z',
                          'limitations': 'No Render/Neon, browser rendering, login hashing, offline sync, or answer-write traffic. Not 100 real students.'}
                print(json.dumps(result, indent=2))
                if result['errors']:
                    raise SystemExit(1)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait()


if __name__ == '__main__':
    main()
