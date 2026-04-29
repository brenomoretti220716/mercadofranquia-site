-- Proposed migration — Fatia ABF enrichment
-- Apenas colunas claramente novas (gaps reais, nao-controversos).
-- Decisoes pendentes (ranges, NOT NULL alters) NAO estao aqui.

BEGIN;

-- 1. Rastreabilidade ABF na Franchise
ALTER TABLE "Franchise" ADD COLUMN "abfUpdatedAt" DATE;
ALTER TABLE "Franchise" ADD COLUMN "dataSource" VARCHAR(50);

-- 2. BusinessModel — gaps confirmados
ALTER TABLE "BusinessModel" ADD COLUMN "headquarter" VARCHAR(191);
ALTER TABLE "BusinessModel" ADD COLUMN "totalUnits" INTEGER;
ALTER TABLE "BusinessModel" ADD COLUMN "advertisingFeeObservation" TEXT;
ALTER TABLE "BusinessModel" ADD COLUMN "royaltiesObservation" TEXT;

COMMIT;

-- 3. NAO incluido — depende de decisao editorial:
--   - ALTER BusinessModel.description SET NULL (decisao 2)
--   - ALTER BusinessModel.photoUrl SET NULL (decisao 2)
--   - Migration de ranges _min/_max (decisao 3)
--   - royalties: NUMERIC -> TEXT (decisao 4)