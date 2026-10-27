"""
One-command script executing Round 3 Hold-Out Test.
Verifies data-only adaptation for unseen questions and rules with zero code changes.
"""

import sys
import subprocess
import os

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("=" * 60)
    print("  ROUND 3 HOLD-OUT TEST RUNNER")
    print("  Adding unseen question and custom rule strictly via data")
    print("=" * 60)

    cmd = [sys.executable, "-m", "pytest", "tests/test_holdout_round3.py", "-v"]
    res = subprocess.run(cmd, cwd=root_dir)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
