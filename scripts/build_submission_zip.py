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
OUTPUT_ZIP = os.path.join(PROJECT_ROOT, "Setu_Submission.zip")

EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "test-results",
    "playwright-report",
    "scratch",
    "dist",
    ".idea",
    ".vscode"
}

EXCLUDED_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip"
}


def make_zip():
    print(f"Building clean submission ZIP: {OUTPUT_ZIP}...")
    if os.path.exists(OUTPUT_ZIP):
        os.remove(OUTPUT_ZIP)

    file_count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in EXCLUDED_EXTS:
                    continue
                if file.startswith(".env") or file == ".DS_Store":
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT).replace("\\", "/")

                # Double check no excluded substring is in rel_path
                if any(ex in rel_path.split("/") for ex in EXCLUDED_DIRS):
                    continue

                zf.write(full_path, rel_path)
                file_count += 1

    # Verify generated ZIP entries
    violations = []
    packaged_entries = []
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as zf:
        for info in zf.infolist():
            packaged_entries.append(info.filename)
            parts = info.filename.replace("\\", "/").split("/")
            for ex in EXCLUDED_DIRS:
                if ex in parts:
                    violations.append(f"Excluded dir '{ex}' in '{info.filename}'")
            _, ext = os.path.splitext(info.filename)
            if ext.lower() in EXCLUDED_EXTS:
                violations.append(f"Excluded extension '{ext}' in '{info.filename}'")
            if info.filename.startswith(".env") or ".git" in parts:
                violations.append(f"Excluded file/git pattern in '{info.filename}'")

    if violations:
        os.remove(OUTPUT_ZIP)
        raise RuntimeError(f"PACKAGING VERIFICATION FAILED:\n" + "\n".join(violations))

    zip_size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"SUCCESS: Packaged {len(packaged_entries)} files into Setu_Submission.zip ({zip_size_mb:.2f} MB).")
    print("Exclusion Verification: PASSED (zero excluded paths found)")
    print("\nComplete Packaged Files List:")
    for entry in sorted(packaged_entries):
        print(f"  {entry}")


if __name__ == "__main__":
    make_zip()
