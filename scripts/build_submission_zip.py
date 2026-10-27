"""
Builds the final submission ZIP for the Setu project.
Strictly excludes:
- node_modules / frontend/node_modules
- .venv / venv / virtual environments
- __pycache__ / *.pyc
- .pytest_cache
- .git repository
- test-results / temporary test artifacts
- secrets / .env files
"""

import os
import zipfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_ZIP = os.path.join(PROJECT_ROOT, "Setu_Final_Submission.zip")

EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "test-results",
    ".idea",
    ".vscode"
}

EXCLUDED_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp"
}


def make_zip():
    print(f"Building final submission ZIP: {OUTPUT_ZIP}...")
    file_count = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Modify dirs in-place to avoid walking excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

            for file in files:
                if file == "Setu_Final_Submission.zip":
                    continue
                _, ext = os.path.splitext(file)
                if ext.lower() in EXCLUDED_EXTS:
                    continue
                if file.startswith(".env") or file == ".DS_Store":
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT)

                zf.write(full_path, rel_path)
                file_count += 1

    zip_size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"Success! Packaged {file_count} files into Setu_Final_Submission.zip ({zip_size_mb:.2f} MB).")


if __name__ == "__main__":
    make_zip()
