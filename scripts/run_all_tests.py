"""
One-command test runner executing the complete Setu test suite across all 9 steps.
"""

import sys
import subprocess
import os

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("=" * 60)
    print("  SETU COMPLETE VERIFICATION SUITE")
    print("  Testing Data Model, Validator, Engine, Teacher Controls,")
    print("  Data Protection, India Fit PWA, Simulation & Hold-Out")
    print("=" * 60)

    cmd = [sys.executable, "-m", "pytest", "tests", "-v", "--durations=5"]
    res = subprocess.run(cmd, cwd=root_dir)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  SOME TESTS FAILED! Check logs above.")
        print("=" * 60)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
