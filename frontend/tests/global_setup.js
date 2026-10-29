import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default async function globalSetup() {
  // Database initialization: scripts/run_e2e_server.py resets and seeds setu_test.db
  // BEFORE uvicorn opens the SQLite file descriptor.
  // Never unlink a live SQLite file descriptor here (especially on Linux/Unix).
}
