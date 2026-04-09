/**
 * Gera um ficheiro .sql com INSERTs para dados de mercado (ABF, ranking, estatísticas da plataforma),
 * ContactInfo, User (ADMIN) e Franchise — com logoUrl, thumbnailUrl e galleryUrls como NULL nas franquias.
 * Origem não é alterada.
 *
 * Uso: npx ts-node scripts/export-admin-franchises-mysql.ts [--output caminho.sql] [--dry-run]
 */

import { PrismaClient, Role, type Franchise } from '@prisma/client';
import { Decimal } from '@prisma/client/runtime/library';
import { writeFile } from 'fs/promises';
import { join } from 'path';
import { escape as sqlEscape } from 'sqlstring';

const prisma = new PrismaClient();

type ScalarRow = Record<string, unknown>;

function toSqlLiteral(value: unknown): string {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  if (typeof value === 'boolean') {
    return value ? '1' : '0';
  }
  if (typeof value === 'number') {
    if (Number.isNaN(value)) {
      return 'NULL';
    }
    return sqlEscape(value);
  }
  if (typeof value === 'bigint') {
    return sqlEscape(value);
  }
  if (value instanceof Date) {
    return sqlEscape(value);
  }
  if (value instanceof Decimal) {
    return sqlEscape(value.toString());
  }
  if (typeof value === 'object') {
    return sqlEscape(JSON.stringify(value));
  }
  if (typeof value === 'string') {
    return sqlEscape(value);
  }
  return sqlEscape(String(value));
}

function buildInsert(
  tableName: string,
  columns: readonly string[],
  row: ScalarRow,
): string {
  const values = columns.map((col) => toSqlLiteral(row[col]));
  const cols = columns.map((c) => `\`${c}\``).join(', ');
  return `INSERT INTO \`${tableName}\` (${cols}) VALUES (${values.join(', ')});`;
}

/** Mesmo que INSERT, mas substitui se a PK/unique existir (útil para reimportar). */
function buildReplace(
  tableName: string,
  columns: readonly string[],
  row: ScalarRow,
): string {
  const values = columns.map((col) => toSqlLiteral(row[col]));
  const cols = columns.map((c) => `\`${c}\``).join(', ');
  return `REPLACE INTO \`${tableName}\` (${cols}) VALUES (${values.join(', ')});`;
}

/** Apenas colunas escalares (Prisma `keyof Model` inclui relações). */
const USER_COLUMNS = [
  'id',
  'name',
  'email',
  'password',
  'role',
  'isActive',
  'createdAt',
  'updatedAt',
  'cpf',
  'phone',
] as const;

const CONTACT_COLUMNS = ['id', 'phone', 'email', 'website'] as const;

const FRANCHISE_COLUMNS = [
  'id',
  'name',
  'slug',
  'headquarterState',
  'segment',
  'subsegment',
  'businessType',
  'franchiseStartYear',
  'abfSince',
  'videoUrl',
  'updatedAt',
  'createdAt',
  'contactId',
  'ownerId',
  'isActive',
  'brandFoundationYear',
  'description',
  'detailedDescription',
  'headquarter',
  'isAbfAssociated',
  'logoUrl',
  'totalUnits',
  'totalUnitsInBrazil',
  'thumbnailUrl',
  'lastScrapedAt',
  'scrapedWebsite',
  'calculationBaseAdFee',
  'calculationBaseRoyaltie',
  'galleryUrls',
  'isReview',
  'averageRating',
  'ratingSum',
  'reviewCount',
  'unitsEvolution',
  'favoritesCount',
  'isSponsored',
  'sponsorPlacements',
  'minimumInvestment',
  'maximumInvestment',
  'minimumReturnOnInvestment',
  'maximumReturnOnInvestment',
  'franchiseFee',
  'averageMonthlyRevenue',
  'royalties',
  'advertisingFee',
  'setupCapital',
  'workingCapital',
  'storeArea',
] as const;

/** Tabela mapeada em Prisma como `RankingBugnumber`. */
const RANKING_BIG_NUMBER_TABLE = 'RankingBugnumber';

const PLATFORM_STATISTICS_COLUMNS = [
  'id',
  'franchisesReviewed',
  'totalReviews',
  'totalSegments',
  'medianRating',
  'updatedAt',
] as const;

const ABF_SEGMENT_ENTRY_COLUMNS = [
  'id',
  'year',
  'quarter',
  'segment',
  'acronym',
  'value',
  'createdAt',
  'updatedAt',
] as const;

const RANKING_BIG_NUMBER_COLUMNS = [
  'id',
  'name',
  'position',
  'growthPercentage',
  'isWorst',
  'isHidden',
  'year',
  'createdAt',
  'updatedAt',
] as const;

function franchiseForExport(f: Franchise): Franchise {
  return {
    ...f,
    logoUrl: null,
    thumbnailUrl: null,
    galleryUrls: null,
    // Campo obrigatório no schema atual; normaliza dumps legados com valor nulo.
    sponsorPlacements: f.sponsorPlacements ?? [],
  };
}

function defaultOutputPath(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return join(process.cwd(), `dump-dados-${y}${m}${day}.sql`);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  let outputPath = defaultOutputPath();
  const outIdx = args.indexOf('--output');
  if (outIdx !== -1 && args[outIdx + 1]) {
    outputPath = args[outIdx + 1];
  }

  const franchises = await prisma.franchise.findMany({
    orderBy: { id: 'asc' },
  });

  const contactIds = [
    ...new Set(
      franchises
        .map((f) => f.contactId)
        .filter((id): id is number => id !== null && id !== undefined),
    ),
  ];

  const contacts = await prisma.contactInfo.findMany({
    where: { id: { in: contactIds } },
    orderBy: { id: 'asc' },
  });

  const admins = await prisma.user.findMany({
    where: { role: Role.ADMIN },
    orderBy: { id: 'asc' },
  });

  const platformStatistics = await prisma.platformStatistics.findMany({
    orderBy: { id: 'asc' },
  });

  const abfSegmentEntries = await prisma.abfSegmentEntry.findMany({
    orderBy: [{ year: 'asc' }, { acronym: 'asc' }],
  });

  const rankingBigNumbers = await prisma.rankingBigNumber.findMany({
    orderBy: [{ year: 'asc' }, { position: 'asc' }],
  });

  console.log(
    `Market: ${platformStatistics.length} platform stat(s), ${abfSegmentEntries.length} ABF segment row(s), ${rankingBigNumbers.length} ranking big number(s).`,
  );
  console.log(
    `Found ${contacts.length} contact row(s), ${admins.length} admin user(s), ${franchises.length} franchise(s).`,
  );

  if (dryRun) {
    console.log('Dry run: no file written.');
    return;
  }

  const header = `-- Dump parcial: dados de mercado (PlatformStatistics, AbfSegmentEntry, RankingBugnumber) +
--   ContactInfo + User (ADMIN) + Franchise
-- Gerado em: ${new Date().toISOString()}
-- Colunas de imagem em Franchise exportadas como NULL: logoUrl, thumbnailUrl, galleryUrls (videoUrl mantido).
-- Passwords de admin incluídas (hashes bcrypt) para login funcionar no ambiente novo.
--
-- IMPORTAÇÃO NO MYSQL DO CLIENTE (base já criada com o schema Prisma):
--   1) Aplicar migrations: npx prisma migrate deploy
--   2) Importar dados:
--      mysql -u USUARIO -p NOME_BASE < ${outputPath.replace(/\\/g, '/')}
--
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

`;

  const footer = `
SET FOREIGN_KEY_CHECKS=1;
`;

  const lines: string[] = [header];

  lines.push('-- Dados de mercado / referência');
  lines.push(
    '-- PlatformStatistics (REPLACE INTO: permite reimportar sem erro de PK duplicada)',
  );
  for (const row of platformStatistics) {
    lines.push(
      buildReplace(
        'PlatformStatistics',
        PLATFORM_STATISTICS_COLUMNS,
        row as ScalarRow,
      ),
    );
  }

  lines.push('');
  lines.push('-- AbfSegmentEntry');
  for (const row of abfSegmentEntries) {
    lines.push(
      buildInsert(
        'AbfSegmentEntry',
        ABF_SEGMENT_ENTRY_COLUMNS,
        row as ScalarRow,
      ),
    );
  }

  lines.push('');
  lines.push('-- RankingBigNumber (tabela MySQL: RankingBugnumber)');
  for (const row of rankingBigNumbers) {
    lines.push(
      buildInsert(
        RANKING_BIG_NUMBER_TABLE,
        RANKING_BIG_NUMBER_COLUMNS,
        row as ScalarRow,
      ),
    );
  }

  lines.push('');
  lines.push('-- ContactInfo');
  for (const c of contacts) {
    lines.push(buildInsert('ContactInfo', CONTACT_COLUMNS, c as ScalarRow));
  }

  lines.push('');
  lines.push('-- User (ADMIN)');
  for (const u of admins) {
    lines.push(buildInsert('User', USER_COLUMNS, u as ScalarRow));
  }

  lines.push('');
  lines.push('-- Franchise (sem paths de imagem)');
  for (const f of franchises) {
    const exported = franchiseForExport(f);
    lines.push(
      buildInsert('Franchise', FRANCHISE_COLUMNS, exported as ScalarRow),
    );
  }

  lines.push(footer);

  await writeFile(outputPath, lines.join('\n'), 'utf8');
  console.log(`Wrote ${outputPath}`);
}

main()
  .catch((e: unknown) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
