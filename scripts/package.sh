#!/usr/bin/env bash
# Shell Packaging Script for Setu
# Produces a clean ZIP without node_modules, venvs, database files, .env, test-results, previous ZIPs, or .git.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ZIP_PATH="$ROOT_DIR/Setu_Submission.zip"

echo "Creating clean submission ZIP at: $ZIP_PATH"

rm -f "$ZIP_PATH"

STAGE_DIR="$ROOT_DIR/scratch/package_staging/Setu"
rm -rf "$ROOT_DIR/scratch/package_staging"
mkdir -p "$STAGE_DIR"

cd "$ROOT_DIR"

# Copy files using rsync or tar while excluding unwanted folders
rsync -av --progress ./ "$STAGE_DIR/" \
  --exclude '.git' \
  --exclude '.pytest_cache' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude 'test-results' \
  --exclude 'playwright-report' \
  --exclude 'scratch' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '*.db' \
  --exclude '*.sqlite' \
  --exclude '*.sqlite3' \
  --exclude '.env*' \
  --exclude '*.zip' \
  --exclude '__pycache__'

cd "$ROOT_DIR/scratch/package_staging"
zip -r "$ZIP_PATH" Setu

rm -rf "$ROOT_DIR/scratch/package_staging"

echo "Clean packaging complete. Output: $ZIP_PATH"
