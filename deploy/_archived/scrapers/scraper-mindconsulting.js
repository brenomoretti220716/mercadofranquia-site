#!/usr/bin/env node
/**
 * scraper-mindconsulting.js
 *
 * Sincroniza dados e imagens da API antiga (apifranchise.mindconsulting.com.br)
 * para o banco MySQL local. Baixa imagens para api/uploads/franchises/.
 *
 * Uso:
 *   node scraper-mindconsulting.js                # sincroniza tudo que falta
 *   node scraper-mindconsulting.js --force         # reprocessa todas
 *   node scraper-mindconsulting.js --resume        # retoma do progresso salvo
 *   node scraper-mindconsulting.js --dry-run       # mostra o que faria sem alterar
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const { randomUUID } = require('crypto');
const mysql = require('mysql2/promise');

// --- Config ---
const SOURCE_API = 'https://apifranchise.mindconsulting.com.br';
const LOCAL_BASE_URL = 'http://localhost:4000';
const UPLOADS_DIR = path.join(__dirname, 'api', 'uploads', 'franchises');
const PROGRESS_FILE = path.join(__dirname, 'scraper-progress.json');
const CONCURRENCY = 2;
const PAGE_SIZE = 50;

const DB_CONFIG = {
  host: 'localhost',
  port: 3306,
  user: 'franchise_user',
  password: 'Kp7mN2vR9xL4qW',
  database: 'franchise_db',
};

// --- CLI args ---
const FORCE = process.argv.includes('--force');
const RESUME = process.argv.includes('--resume');
const DRY_RUN = process.argv.includes('--dry-run');

// --- Stats ---
const stats = { processed: 0, updated: 0, skipped: 0, images: 0, errors: 0 };

// --- Progress tracking ---
function loadProgress() {
  if (!RESUME) return new Set();
  try {
    const data = JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8'));
    console.log(`Resuming: ${data.completed.length} already done`);
    return new Set(data.completed);
  } catch {
    return new Set();
  }
}

function saveProgress(completedSet) {
  fs.writeFileSync(
    PROGRESS_FILE,
    JSON.stringify({
      timestamp: new Date().toISOString(),
      stats,
      completed: [...completedSet],
    }),
  );
}

// --- Image download ---
function downloadFile(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, { timeout: 30000 }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return downloadFile(res.headers.location).then(resolve).catch(reject);
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
        }
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve(Buffer.concat(chunks)));
        res.on('error', reject);
      })
      .on('error', reject)
      .on('timeout', function () {
        this.destroy();
        reject(new Error(`Timeout for ${url}`));
      });
  });
}

async function downloadAndSaveImage(imageUrl) {
  if (!imageUrl || imageUrl === 'null') return null;

  // Extract extension from URL
  const urlPath = new URL(imageUrl).pathname;
  const ext = path.extname(urlPath) || '.jpg';
  const filename = `${randomUUID()}${ext}`;
  const filepath = path.join(UPLOADS_DIR, filename);

  try {
    const buffer = await downloadFile(imageUrl);
    if (buffer.length < 100) return null; // skip tiny/empty files
    fs.writeFileSync(filepath, buffer);
    stats.images++;
    return `${LOCAL_BASE_URL}/uploads/franchises/${filename}`;
  } catch (err) {
    console.error(`    [img-err] ${imageUrl}: ${err.message}`);
    return null;
  }
}

// --- Fetch from source API ---
async function fetchAllFromSource() {
  const allFranchises = [];
  let page = 1;

  while (true) {
    const url = `${SOURCE_API}/franchises?page=${page}&limit=${PAGE_SIZE}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Source API error: ${res.status}`);
    const data = await res.json();

    allFranchises.push(...data.data);
    console.log(`Fetched page ${page}/${Math.ceil(data.total / PAGE_SIZE)} (${allFranchises.length}/${data.total})`);

    if (allFranchises.length >= data.total) break;
    page++;
  }

  return allFranchises;
}

// --- Process a single franchise ---
async function processFranchise(source, db, completed) {
  const slug = source.slug;
  if (!slug) return;
  if (completed.has(slug)) {
    stats.skipped++;
    return;
  }

  // Get local record
  const [rows] = await db.query(
    'SELECT id, logoUrl, thumbnailUrl, galleryUrls, description, detailedDescription, segment, subsegment, businessType, minimumInvestment, maximumInvestment, franchiseFee, averageMonthlyRevenue, setupCapital, workingCapital, royalties, advertisingFee, brandFoundationYear, franchiseStartYear, abfSince, headquarter, storeArea, totalUnits FROM Franchise WHERE slug = ?',
    [slug],
  );

  if (rows.length === 0) {
    stats.skipped++;
    return;
  }

  const local = rows[0];
  const updates = {};

  // --- Images: download only if local is empty ---
  // Logo
  if ((!local.logoUrl || FORCE) && source.logoUrl) {
    const localUrl = await downloadAndSaveImage(source.logoUrl);
    if (localUrl) updates.logoUrl = localUrl;
  }

  // Thumbnail
  if ((!local.thumbnailUrl || FORCE) && source.thumbnailUrl) {
    const localUrl = await downloadAndSaveImage(source.thumbnailUrl);
    if (localUrl) updates.thumbnailUrl = localUrl;
  }

  // Gallery
  if ((!local.galleryUrls || FORCE) && source.galleryUrls) {
    try {
      const gallery =
        typeof source.galleryUrls === 'string'
          ? JSON.parse(source.galleryUrls)
          : source.galleryUrls;

      if (Array.isArray(gallery) && gallery.length > 0) {
        const localUrls = [];
        for (const imgUrl of gallery) {
          const localUrl = await downloadAndSaveImage(imgUrl);
          if (localUrl) localUrls.push(localUrl);
        }
        if (localUrls.length > 0) {
          updates.galleryUrls = JSON.stringify(localUrls);
        }
      }
    } catch {}
  }

  // --- Text/data fields: fill only if local is null/empty ---
  const fieldMap = {
    description: 'description',
    detailedDescription: 'detailedDescription',
    segment: 'segment',
    subsegment: 'subsegment',
    businessType: 'businessType',
    headquarter: 'headquarter',
  };

  for (const [srcKey, dbKey] of Object.entries(fieldMap)) {
    if ((!local[dbKey] || local[dbKey] === '') && source[srcKey]) {
      updates[dbKey] = source[srcKey];
    }
  }

  // --- Numeric fields ---
  const numericFields = {
    minimumInvestment: 'minimumInvestment',
    maximumInvestment: 'maximumInvestment',
    franchiseFee: 'franchiseFee',
    averageMonthlyRevenue: 'averageMonthlyRevenue',
    setupCapital: 'setupCapital',
    workingCapital: 'workingCapital',
    royalties: 'royalties',
    advertisingFee: 'advertisingFee',
    storeArea: 'storeArea',
    totalUnits: 'totalUnits',
  };

  for (const [srcKey, dbKey] of Object.entries(numericFields)) {
    if (local[dbKey] == null && source[srcKey] != null) {
      updates[dbKey] = source[srcKey];
    }
  }

  // --- Integer fields ---
  const intFields = {
    brandFoundationYear: 'brandFoundationYear',
    franchiseStartYear: 'franchiseStartYear',
    abfSince: 'abfSince',
  };

  for (const [srcKey, dbKey] of Object.entries(intFields)) {
    if (local[dbKey] == null && source[srcKey] != null) {
      updates[dbKey] = source[srcKey];
    }
  }

  // --- Apply updates ---
  stats.processed++;

  if (Object.keys(updates).length === 0) {
    stats.skipped++;
    completed.add(slug);
    return;
  }

  if (DRY_RUN) {
    console.log(`  [dry-run] ${slug}: would update ${Object.keys(updates).join(', ')}`);
    stats.updated++;
    completed.add(slug);
    return;
  }

  const setClauses = Object.keys(updates)
    .map((k) => `\`${k}\` = ?`)
    .join(', ');
  const values = Object.values(updates);

  await db.query(`UPDATE Franchise SET ${setClauses} WHERE slug = ?`, [
    ...values,
    slug,
  ]);

  stats.updated++;
  completed.add(slug);

  const imgCount = [updates.logoUrl, updates.thumbnailUrl, updates.galleryUrls].filter(Boolean).length;
  const dataCount = Object.keys(updates).length - imgCount;
  console.log(
    `  [${stats.processed}] ${slug}: ${imgCount} images, ${dataCount} fields updated`,
  );
}

// --- Concurrency helper ---
async function runWithConcurrency(items, concurrency, fn) {
  let index = 0;
  const workers = Array.from({ length: concurrency }, async () => {
    while (index < items.length) {
      const i = index++;
      try {
        await fn(items[i], i);
      } catch (err) {
        stats.errors++;
        console.error(`  [error] ${items[i]?.slug}: ${err.message}`);
      }
    }
  });
  await Promise.all(workers);
}

// --- Main ---
async function main() {
  console.log('=== scraper-mindconsulting ===');
  console.log(`Source: ${SOURCE_API}`);
  console.log(`Mode: ${DRY_RUN ? 'DRY RUN' : FORCE ? 'FORCE' : 'fill-empty'}`);
  console.log(`Concurrency: ${CONCURRENCY}`);
  console.log('');

  // Ensure uploads dir
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });

  // Load progress
  const completed = loadProgress();

  // Fetch all from source
  console.log('Fetching from source API...');
  const sourceFranchises = await fetchAllFromSource();
  console.log(`Source: ${sourceFranchises.length} franchises\n`);

  // Connect to local DB
  const db = await mysql.createConnection(DB_CONFIG);
  console.log('Connected to local MySQL\n');

  // Process
  await runWithConcurrency(sourceFranchises, CONCURRENCY, async (source) => {
    await processFranchise(source, db, completed);

    // Save progress every 50
    if (stats.processed % 50 === 0 && stats.processed > 0) {
      saveProgress(completed);
      console.log(
        `  --- progress: ${stats.processed} processed, ${stats.updated} updated, ${stats.images} images, ${stats.errors} errors ---`,
      );
    }
  });

  // Final save
  saveProgress(completed);
  await db.end();

  console.log('\n=== Done ===');
  console.log(`  Processed: ${stats.processed}`);
  console.log(`  Updated:   ${stats.updated}`);
  console.log(`  Skipped:   ${stats.skipped}`);
  console.log(`  Images:    ${stats.images}`);
  console.log(`  Errors:    ${stats.errors}`);
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
