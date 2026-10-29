"""
Cross-platform E2E Test Server Launcher
Resets and seeds the isolated setu_test.db BEFORE uvicorn opens the file.
This prevents open-file-descriptor unlinking issues on Linux/Unix.
"""
import os
import sys
import subprocess
from pathlib import Path
from sqlalchemy import URL

def main():
    repo_root = Path(__file__).resolve().parent.parent
    backend_dir = repo_root / "backend"
    scripts_dir = repo_root / "scripts"
    db_file = (backend_dir / "setu_test.db").resolve()
    seed_script = scripts_dir / "seed_e2e_fixtures.py"

    # 1. Clean up any existing test DB files before server opens them
    for f in [db_file, backend_dir / "setu_test.db-journal", backend_dir / "setu_test.db-wal", backend_dir / "setu_test.db-shm"]:
        if f.exists():
            try:
                f.unlink()
            except Exception as e:
                print(f"[run_e2e_server] Warning removing {f}: {e}")

    # 2. Absolute SQLite URL using SQLAlchemy URL construction (handles Linux 4-slash absolute vs relative)
    db_uri = URL.create("sqlite", database=str(db_file)).render_as_string(hide_password=False)
    env = os.environ.copy()
    env["SETU_TEST_ENV"] = "1"
    env["DATABASE_URL"] = db_uri

    # 3. Seed fixtures synchronously before server startup
    print(f"[run_e2e_server] Seeding test database at {db_file} (URI: {db_uri})...")
    subprocess.run(
        [sys.executable, str(seed_script)],
        env=env,
        cwd=str(backend_dir),
        check=True
    )
    print("[run_e2e_server] Seeding complete.")

    # 4. Start uvicorn server with the exact same DB
    print("[run_e2e_server] Launching uvicorn on port 8000...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000"
    ]
    sys.exit(subprocess.call(cmd, env=env, cwd=str(backend_dir)))

if __name__ == "__main__":
    main()

