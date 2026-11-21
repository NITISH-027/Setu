"""Fresh local demo database behavior, isolated from all shared fixtures."""
import os
from pathlib import Path
import subprocess
import sys


def test_fresh_demo_database_lists_no_students_but_has_teacher_entry(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp_path / 'empty_demo_test.db'}", SETU_DEMO_MODE="true", ENV="development")
    result = subprocess.run([sys.executable, "-c", """
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.get('/api/auth/demo-students')
    assert response.status_code == 200, response.text
    assert response.json() == {'students': []}, response.text
    assert client.post('/api/auth/demo-login', json={'profile': 'teacher'}).status_code == 200
    assert client.post('/api/auth/demo-login', json={'profile': 'student:missing'}).status_code == 404
"""], cwd=root / "backend", env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
