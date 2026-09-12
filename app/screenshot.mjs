// Снимки экранов живого интерфейса. Запускает сервер на 8766, снимает четыре страницы, останавливает сервер.
//   node app/screenshot.mjs [outDir=app/screenshots]
// Нужен playwright с Chromium (npm i -g playwright && npx playwright install chromium).
// FONT_DIR — локальный кэш Google Fonts (см. docs/mockup/README.md), если сеть недоступна.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const outDir = process.argv[2] || path.join('app', 'screenshots');
fs.mkdirSync(outDir, { recursive: true });
const PORT = 8766, BASE = `http://127.0.0.1:${PORT}/`;
const server = spawn('python3', ['app/server.py', '--port', String(PORT)], { stdio: ['ignore', 'pipe', 'inherit'] });
for (let i = 0; i < 60; i++) { try { const r = await fetch(BASE); if (r.ok) break; } catch {} await new Promise((r) => setTimeout(r, 250)); }
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
const fontDir = process.env.FONT_DIR;
if (fontDir) await page.route(/^https:\/\/fonts\.googleapis\.com\//, (route) => {
  const u = new URL(route.request().url());
  if (u.pathname.endsWith('.woff2')) return route.fulfill({ path: path.join(fontDir, path.basename(u.pathname)), contentType: 'font/woff2' });
  return route.fulfill({ path: path.join(fontDir, 'local-fonts.css'), contentType: 'text/css' });
});
try {
  for (const p of ['portfolio', 'compare', 'stress', 'data']) {
    await page.goto(BASE + '#' + p, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, `${p}.png`), fullPage: true });
    console.log('wrote', p + '.png');
  }
} finally {
  await browser.close();
  server.kill();
}
