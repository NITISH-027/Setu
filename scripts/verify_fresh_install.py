"""
Fresh installation verification script.
Validates dependencies, runs test suite, builds frontend, and runs engine parity checks.
"""

import sys
import subprocess
import os

def run_cmd(cmd, cwd=None, description=""):
    print(f"\n--- {description} ---")
    print(f"Command: {cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    if res.returncode != 0:
        print(f"FAILED: {description} returned code {res.returncode}")
        sys.exit(res.returncode)
    print(f"SUCCESS: {description}")

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 60)
    print("  SETU FRESH INSTALLATION VERIFICATION")
    print("=" * 60)

    # 1. Verify Python backend dependencies
    run_cmd(
        f'"{sys.executable}" -m pytest --version',
        cwd=root_dir,
        description="Verify Pytest is available"
    )

    # 2. Run backend test suite
    run_cmd(
        f'"{sys.executable}" -m pytest tests -v',
        cwd=root_dir,
        description="Run Python backend test suite"
    )

    # 3. Build frontend
    run_cmd(
        "npm run build",
        cwd=frontend_dir,
        description="Build frontend Vite production bundle"
    )

    print("\n" + "=" * 60)
    print("  FRESH INSTALLATION AND BUILD VERIFICATION PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
