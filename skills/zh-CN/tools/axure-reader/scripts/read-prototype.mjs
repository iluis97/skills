#!/usr/bin/env node
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawn } = require('node:child_process');
const { fileURLToPath } = require('node:url');

function parseArgs(args) {
  const opts = { output: path.join(os.tmpdir(), `axure-reader-${Date.now()}`), wait: 5000, urls: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output' || args[i] === '--wait-ms') {
      if (!args[i + 1]) throw new Error(`Missing value for ${args[i]}`);
      if (args[i] === '--output') opts.output = path.resolve(args[++i]);
      else opts.wait = Number(args[++i]);
    } else if (args[i].startsWith('--')) throw new Error(`Unknown option: ${args[i]}`);
    else opts.urls.push(args[i]);
  }
  if (!opts.urls.length || !Number.isFinite(opts.wait) || opts.wait < 0) throw new Error('Usage: node read-prototype.mjs [--output DIR] [--wait-ms N] URL [URL ...]');
  return opts;
}
function loadPlaywright() {
  const candidates = [process.env.AXURE_PLAYWRIGHT_PATH, 'playwright', path.join(os.homedir(), '.cache', 'axure-extractor', 'node_modules', 'playwright')].filter(Boolean);
  for (const candidate of candidates) {
    try { return require(candidate); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
  }
  throw new Error('Playwright not found. See references/troubleshooting.md.');
}
function pageNameFor(url, frames) {
  const u = new URL(url);
  const hash = new URLSearchParams(u.hash.replace(/^#/, ''));
  const named = u.searchParams.get('p') || hash.get('p');
  if (named) return named;
  const content = frames.find(f => f.index > 0 && /\.html(?:[?#]|$)/i.test(f.url));
  const pathname = content ? new URL(content.url).pathname : u.pathname;
  const last = pathname.split('/').pop();
  return last && /\.html$/i.test(last) && !/^(start|index)\.html$/i.test(last) ? decodeURIComponent(last.replace(/\.html$/i, '')) : null;
}
async function runOfficial(url, pageName, dir) {
  if (!pageName || pageName.includes(',')) return { status: 'skipped', reason: 'Target page cannot be safely selected; inspect sitemap and select explicitly.' };
  const extractor = path.join(path.dirname(fileURLToPath(import.meta.url)), 'axhub', 'extract.mjs');
  const output = path.join(dir, 'official');
  const args = [extractor, url, '--pages', pageName, '--advanced', '-o', output];
  return await new Promise(resolve => {
    const child = spawn(process.execPath, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let log = ''; let timedOut = false;
    child.stdout.on('data', d => { log += d; });
    child.stderr.on('data', d => { log += d; });
    const timer = setTimeout(() => { timedOut = true; child.kill(); }, 180000);
    child.on('error', e => { clearTimeout(timer); resolve({ status: 'failed', error: e.message }); });
    child.on('close', code => {
      clearTimeout(timer);
      fs.mkdirSync(output, { recursive: true });
      fs.writeFileSync(path.join(output, 'extract.log'), log, 'utf8');
      const pages = path.join(output, 'pages');
      const artifacts = fs.existsSync(pages) ? fs.readdirSync(pages, { withFileTypes: true }).filter(x => x.isDirectory()).map(x => x.name) : [];
      const files = artifacts.flatMap(name => fs.readdirSync(path.join(pages, name)).map(file => `${name}/${file}`));
      resolve({ status: timedOut ? 'timeout' : code === 0 && artifacts.length ? 'finished' : 'failed', exitCode: code, selectedPage: pageName, artifacts, files, output, note: 'Check extract.log and individual files for partial failures; finished does not imply completeness.' });
    });
  });
}
async function main() {
  const opts = parseArgs(process.argv.slice(2));
  fs.mkdirSync(opts.output, { recursive: true });
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const [index, url] of opts.urls.entries()) {
      const dir = path.join(opts.output, String(index + 1).padStart(3, '0'));
      fs.mkdirSync(dir, { recursive: true });
      const result = { index: index + 1, url, status: 'failed', frames: [], warnings: [] };
      let context;
      try {
        const parsed = new URL(url);
        if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Only HTTP(S) URLs are supported');
        context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
        const page = await context.newPage();
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
        if (response && response.status() >= 400) throw new Error(`HTTP ${response.status()}`);
        await page.waitForTimeout(opts.wait);
        const notice = page.getByText('知道了', { exact: true });
        if (await notice.count()) await notice.first().click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(1000);
        result.title = await page.title();
        result.finalUrl = page.url();
        for (const [frameIndex, frame] of page.frames().entries()) {
          const frameInfo = { index: frameIndex, url: frame.url() };
          try {
            frameInfo.title = await frame.title();
            frameInfo.text = await frame.locator('body').innerText({ timeout: 5000 });
          } catch (e) { frameInfo.error = e.message; result.warnings.push(`Frame ${frameIndex}: text unavailable`); }
          result.frames.push(frameInfo);
        }
        await page.screenshot({ path: path.join(dir, 'viewport.png') });
        const contentFrame = page.frames().find(f => f !== page.mainFrame() && f.url() !== 'about:blank');
        if (contentFrame) {
          try { await contentFrame.locator('body').screenshot({ path: path.join(dir, 'page.png'), timeout: 15000 }); }
          catch (e) { result.warnings.push(`Page screenshot unavailable: ${e.message}`); }
        } else result.warnings.push('No content iframe found; verify target and screenshot manually.');
        const meaningful = result.frames.some(f => f.text && f.text.trim());
        result.status = meaningful ? 'captured' : 'partial';
        result.warnings.push('Verify target page, completeness and dynamic interactions manually.');
        fs.writeFileSync(path.join(dir, 'content.md'), result.frames.map(f => `## Frame ${f.index}: ${f.url}\n\n${f.text || f.error || ''}`).join('\n\n'), 'utf8');
      } catch (e) { result.error = e.message; }
      finally { if (context) await context.close(); }
      try { result.official = await runOfficial(url, pageNameFor(url, result.frames), dir); }
      catch (e) { result.official = { status: 'failed', error: e.message }; }
      fs.writeFileSync(path.join(dir, 'page.json'), JSON.stringify(result, null, 2), 'utf8');
      results.push(result);
      console.log(`${result.index}: ${result.status} ${url}${result.error ? ' - ' + result.error : ''}`);
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(opts.output, 'manifest.json'), JSON.stringify(results.map(({frames, ...r}) => r), null, 2), 'utf8');
  console.log(`Output: ${opts.output}`);
  if (results.some(r => r.status !== 'captured')) process.exitCode = 1;
}
main().catch(e => { console.error(e.message); process.exitCode = 1; });