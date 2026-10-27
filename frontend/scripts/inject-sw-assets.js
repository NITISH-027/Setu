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
  const baseAssets = [
    '/',
    '/index.html',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png'
  ];
  const allAssets = [...baseAssets, ...assetFiles];
  const assetsJson = JSON.stringify(allAssets, null, 2);

  const updateSwContent = (filePath) => {
    if (!fs.existsSync(filePath)) return;
    let content = fs.readFileSync(filePath, 'utf-8');
    content = content.replace(/const STATIC_ASSETS = \[[\s\S]*?\];/, `const STATIC_ASSETS = ${assetsJson};`);
    fs.writeFileSync(filePath, content, 'utf-8');
    console.log(`Updated precached assets in ${filePath}:`, assetFiles);
  };

  updateSwContent(distSwPath);
  updateSwContent(publicSwPath);
}
