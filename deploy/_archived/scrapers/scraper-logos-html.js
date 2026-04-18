#!/usr/bin/env node
/**
 * scraper-logos-html.js
 *
 * Para as franquias restantes sem logo, scrape o site diretamente
 * procurando por <img> que parece ser logo (header, class/id "logo", og:image).
 *
 * Uso: node scraper-logos-html.js [--dry-run]
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const { randomUUID } = require('crypto');
const mysql = require('mysql2/promise');

const UPLOADS_DIR = path.join(__dirname, 'api', 'uploads', 'franchises');
const CONCURRENCY = 2;
const DRY_RUN = process.argv.includes('--dry-run');
const DB_CONFIG = {
  host: 'localhost', port: 3306,
  user: 'franchise_user', password: 'Kp7mN2vR9xL4qW', database: 'franchise_db',
};
const stats = { processed: 0, updated: 0, skipped: 0, errors: 0 };

function fetchBuffer(url, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) return reject(new Error('Too many redirects'));
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, { timeout: 15000, headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        const next = res.headers.location.startsWith('http')
          ? res.headers.location
          : new URL(res.headers.location, url).href;
        res.resume();
        return fetchBuffer(next, maxRedirects - 1).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) { res.resume(); return reject(new Error(`HTTP ${res.statusCode}`)); }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ buffer: Buffer.concat(chunks), contentType: res.headers['content-type'] || '' }));
      res.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', function () { this.destroy(); reject(new Error('Timeout')); });
  });
}

function extractDomain(websiteUrl) {
  try {
    const fixed = websiteUrl.replace(/,/g, '.'); // fix typos like .com,br
    const u = new URL(fixed.startsWith('http') ? fixed : `http://${fixed}`);
    return u.origin;
  } catch { return null; }
}

function resolveUrl(src, base) {
  if (!src) return null;
  if (src.startsWith('data:')) return null;
  if (src.startsWith('//')) return `https:${src}`;
  if (src.startsWith('http')) return src;
  try { return new URL(src, base).href; } catch { return null; }
}

function extractLogoCandidates(html, baseUrl) {
  const candidates = [];

  // 1. og:image
  const ogMatch = html.match(/<meta[^>]*property=["']og:image["'][^>]*content=["']([^"']+)["']/i)
    || html.match(/<meta[^>]*content=["']([^"']+)["'][^>]*property=["']og:image["']/i);
  if (ogMatch) candidates.push({ url: resolveUrl(ogMatch[1], baseUrl), priority: 3, source: 'og:image' });

  // 2. <img> with class/id/alt containing "logo"
  const logoImgRegex = /<img[^>]*(?:class|id|alt)=["'][^"']*logo[^"']*["'][^>]*src=["']([^"']+)["']/gi;
  let m;
  while ((m = logoImgRegex.exec(html)) !== null) {
    candidates.push({ url: resolveUrl(m[1], baseUrl), priority: 5, source: 'img[logo]' });
  }

  // Also match src before class/id/alt
  const logoImgRegex2 = /<img[^>]*src=["']([^"']+)["'][^>]*(?:class|id|alt)=["'][^"']*logo[^"']*["']/gi;
  while ((m = logoImgRegex2.exec(html)) !== null) {
    candidates.push({ url: resolveUrl(m[1], baseUrl), priority: 5, source: 'img[logo]' });
  }

  // 3. apple-touch-icon
  const touchMatch = html.match(/<link[^>]*rel=["']apple-touch-icon["'][^>]*href=["']([^"']+)["']/i);
  if (touchMatch) candidates.push({ url: resolveUrl(touchMatch[1], baseUrl), priority: 2, source: 'apple-touch-icon' });

  // 4. Any <img> in <header>
  const headerMatch = html.match(/<header[^>]*>([\s\S]*?)<\/header>/i);
  if (headerMatch) {
    const headerImgs = /<img[^>]*src=["']([^"']+)["']/gi;
    while ((m = headerImgs.exec(headerMatch[1])) !== null) {
      candidates.push({ url: resolveUrl(m[1], baseUrl), priority: 1, source: 'header img' });
    }
  }

  // Deduplicate and sort by priority (highest first)
  const seen = new Set();
  return candidates
    .filter(c => c.url && !seen.has(c.url) && (seen.add(c.url), true))
    .sort((a, b) => b.priority - a.priority);
}

async function tryDownloadLogo(candidates) {
  for (const candidate of candidates) {
    try {
      const { buffer, contentType } = await fetchBuffer(candidate.url);
      // Must be an image > 1KB (skip tiny favicons and placeholder gifs)
      if (buffer.length > 1000 && (contentType.includes('image') || contentType.includes('svg') || candidate.url.match(/\.(png|jpg|jpeg|svg|webp)$/i))) {
        return { buffer, contentType, source: candidate.source, url: candidate.url };
      }
    } catch {}
  }
  return null;
}

function extFromUrl(url, contentType) {
  if (contentType.includes('svg')) return '.svg';
  if (contentType.includes('png')) return '.png';
  if (contentType.includes('webp')) return '.webp';
  const urlExt = path.extname(new URL(url).pathname).toLowerCase();
  if (['.png', '.jpg', '.jpeg', '.svg', '.webp'].includes(urlExt)) return urlExt;
  return '.png';
}

async function processFranchise(row, db) {
  const { slug, website } = row;
  const baseUrl = extractDomain(website);
  if (!baseUrl) { stats.skipped++; return; }

  stats.processed++;

  try {
    const { buffer: htmlBuffer } = await fetchBuffer(baseUrl);
    const html = htmlBuffer.toString('utf8');
    const candidates = extractLogoCandidates(html, baseUrl);

    if (candidates.length === 0) { stats.skipped++; return; }

    const result = await tryDownloadLogo(candidates);
    if (!result) { stats.skipped++; return; }

    if (DRY_RUN) {
      console.log(`  [dry-run] ${slug}: ${result.source} (${result.buffer.length} bytes) from ${result.url.substring(0, 80)}`);
      stats.updated++;
      return;
    }

    const ext = extFromUrl(result.url, result.contentType);
    const filename = `${randomUUID()}${ext}`;
    fs.writeFileSync(path.join(UPLOADS_DIR, filename), result.buffer);
    const logoUrl = `/uploads/franchises/${filename}`;

    await db.query('UPDATE Franchise SET logoUrl = ? WHERE slug = ?', [logoUrl, slug]);
    stats.updated++;
    console.log(`  [${stats.processed}] ${slug}: ${result.source} → ${filename} (${result.buffer.length} bytes)`);
  } catch (e) {
    stats.skipped++;
  }
}

async function main() {
  console.log(`=== scraper-logos-html ${DRY_RUN ? '(DRY RUN)' : ''} ===\n`);
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
  const db = await mysql.createConnection(DB_CONFIG);

  const [rows] = await db.query(`
    SELECT f.slug, c.website
    FROM Franchise f
    JOIN ContactInfo c ON f.contactId = c.id
    WHERE (f.logoUrl IS NULL OR f.logoUrl = '')
      AND c.website IS NOT NULL AND c.website != ''
  `);

  console.log(`${rows.length} franchises to process\n`);

  let i = 0;
  await Promise.all(Array.from({ length: CONCURRENCY }, async () => {
    while (i < rows.length) {
      const idx = i++;
      try { await processFranchise(rows[idx], db); }
      catch (e) { stats.errors++; console.error(`  [error] ${rows[idx]?.slug}: ${e.message}`); }
    }
  }));

  await db.end();
  console.log('\n=== Done ===');
  console.log(`  Processed: ${stats.processed}`);
  console.log(`  Updated:   ${stats.updated}`);
  console.log(`  Skipped:   ${stats.skipped}`);
  console.log(`  Errors:    ${stats.errors}`);
}

main().catch(err => { console.error('Fatal:', err); process.exit(1); });
