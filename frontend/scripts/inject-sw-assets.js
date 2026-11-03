import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distDir = path.resolve(__dirname, '..', 'dist');
const assetsDir = path.resolve(distDir, 'assets');
const distSwPath = path.resolve(distDir, 'sw.js');
const publicSwPath = path.resolve(__dirname, '..', 'public', 'sw.js');

if (fs.existsSync(assetsDir)) {
  const assetFiles = fs.readdirSync(assetsDir).map(f => `/assets/${f}`);
  const distSwPath = path.resolve(distDir, 'sw.js');
  if (fs.existsSync(distSwPath)) {
    console.log(`Build complete. Built asset files in ${assetsDir}:`, assetFiles);
  }
}
