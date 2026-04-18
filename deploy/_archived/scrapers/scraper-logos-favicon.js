#!/usr/bin/env node
/**
 * scraper-logos-favicon.js
 *
 * Para franquias sem logoUrl mas com website, tenta:
 * 1. Extrair og:image ou apple-touch-icon do site
 * 2. Fallback: Google Favicon API (128px)
 *
 * Uso:
 *   node scraper-logos-favicon.js              # preenche logos faltantes
 *   node scraper-logos-favicon.js --dry-run    # mostra o que faria
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const { randomUUID } = require('crypto');
const mysql = require('mysql2/promise');

const LOCAL_BASE_URL = 'http://localhost:4000';
const UPLOADS_DIR = path.join(__dirname, 'api', 'uploads', 'franchises');
const CONCURRENCY = 3;
const DRY_RUN = process.argv.includes('--dry-run');

const DB_CONFIG = {
  host: 'localhost',
  port: 3306,
  user: 'franchise_user',
  password: 'Kp7mN2vR9xL4qW',
  database: 'franchise_db',
};

const stats = { processed: 0, updated: 0, skipped: 0, errors: 0 };

function fetchBuffer(url, maxRedirects = 3) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) return reject(new Error('Too many redirects'));
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, { timeout: 15000, headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          const next = res.headers.location.startsWith('http')
            ? res.headers.location
            : new URL(res.headers.location, url).href;
          res.resume();
          return fetchBuffer(next, maxRedirects - 1).then(resolve).catch(reject);
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${res.statusCode}`));
        }
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ buffer: Buffer.concat(chunks), contentType: res.headers['content-type'] || '' }));
        res.on('error', reject);
      })
      .on('error', reject)
      .on('timeout', function () { this.destroy(); reject(new Error('Timeout')); });
  });
}

function fetchText(url) {
  return fetchBuffer(url).then(({ buffer }) => buffer.toString('utf8'));
}

function extractDomain(websiteUrl) {
  try {
    return new URL(websiteUrl.startsWith('http') ? websiteUrl : `http://${websiteUrl}`).hostname;
  } catch {
    return null;
  }
}

async function tryOgImage(websiteUrl) {
  try {
    const html = await fetchText(websiteUrl);

    // Try og:image
    const ogMatch = html.match(/<meta[^>]*property=["']og:image["'][^>]*content=["']([^"']+)["']/i)
      || html.match(/<meta[^>]*content=["']([^"']+)["'][^>]*property=["']og:image["']/i);
    if (ogMatch && ogMatch[1]) {
      const imgUrl = ogMatch[1].startsWith('http') ? ogMatch[1] : new URL(ogMatch[1], websiteUrl).href;
      const { buffer, contentType } = await fetchBuffer(imgUrl);
      if (buffer.length > 1000 && contentType.includes('image')) return { buffer, contentType };
    }

    // Try apple-touch-icon (usually 180x180)
    const touchMatch = html.match(/<link[^>]*rel=["']apple-touch-icon["'][^>]*href=["']([^"']+)["']/i);
    if (touchMatch && touchMatch[1]) {
      const imgUrl = touchMatch[1].startsWith('http') ? touchMatch[1] : new URL(touchMatch[1], websiteUrl).href;
      const { buffer, contentType } = await fetchBuffer(imgUrl);
      if (buffer.length > 500 && contentType.includes('image')) return { buffer, contentType };
    }
  } catch {}
  return null;
}

async function tryGoogleFavicon(domain) {
  try {
    const url = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
    const { buffer, contentType } = await fetchBuffer(url);
    // Google returns a default globe icon (~726 bytes) for unknown domains
    if (buffer.length > 1000 && contentType.includes('image')) return { buffer, contentType };
  } catch {}
  return null;
}

function extFromContentType(ct) {
  if (ct.includes('png')) return '.png';
  if (ct.includes('svg')) return '.svg';
  if (ct.includes('webp')) return '.webp';
  if (ct.includes('gif')) return '.gif';
  return '.jpg';
}

async function saveImage(buffer, contentType) {
  const ext = extFromContentType(contentType);
  const filename = `${randomUUID()}${ext}`;
  fs.writeFileSync(path.join(UPLOADS_DIR, filename), buffer);
  return `/uploads/franchises/${filename}`;
}

async function processFranchise(row, db) {
  const { slug, website } = row;
  const domain = extractDomain(website);
  if (!domain) { stats.skipped++; return; }

  stats.processed++;

  // Strategy 1: og:image or apple-touch-icon from the site
  let result = await tryOgImage(website.startsWith('http') ? website : `http://${website}`);

  // Strategy 2: Google Favicon API
  if (!result) {
    result = await tryGoogleFavicon(domain);
  }

  if (!result) {
    stats.skipped++;
    return;
  }

  if (DRY_RUN) {
    console.log(`  [dry-run] ${slug} (${domain}): would save ${result.buffer.length} bytes`);
    stats.updated++;
    return;
  }

  const logoUrl = await saveImage(result.buffer, result.contentType);
  await db.query('UPDATE Franchise SET logoUrl = ? WHERE slug = ?', [logoUrl, slug]);
  stats.updated++;
  console.log(`  [${stats.processed}] ${slug}: saved ${result.buffer.length} bytes → ${path.basename(logoUrl)}`);
}

async function runWithConcurrency(items, concurrency, fn) {
  let i = 0;
  await Promise.all(
    Array.from({ length: concurrency }, async () => {
      while (i < items.length) {
        const idx = i++;
        try { await fn(items[idx]); } catch (e) {
          stats.errors++;
          console.error(`  [error] ${items[idx]?.slug}: ${e.message}`);
        }
      }
    }),
  );
}

async function main() {
  console.log(`=== scraper-logos-favicon ${DRY_RUN ? '(DRY RUN)' : ''} ===\n`);
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });

  const db = await mysql.createConnection(DB_CONFIG);

  const [rows] = await db.query(`
    SELECT f.slug, c.website
    FROM Franchise f
    JOIN ContactInfo c ON f.contactId = c.id
    WHERE (f.logoUrl IS NULL OR f.logoUrl = '')
      AND c.website IS NOT NULL AND c.website != ''
  `);

  console.log(`${rows.length} franchises without logo but with website\n`);

  await runWithConcurrency(rows, CONCURRENCY, (row) => processFranchise(row, db));

  await db.end();

  console.log('\n=== Done ===');
  console.log(`  Processed: ${stats.processed}`);
  console.log(`  Updated:   ${stats.updated}`);
  console.log(`  Skipped:   ${stats.skipped} (no image found)`);
  console.log(`  Errors:    ${stats.errors}`);
}

main().catch((err) => { console.error('Fatal:', err); process.exit(1); });
