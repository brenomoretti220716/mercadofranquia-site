import { Injectable, Logger } from '@nestjs/common';
import * as cheerio from 'cheerio';
import { ImageProcessorService } from '../franchises/imports/image-processor.service';
import { FranchisePersistenceService } from '../franchises/imports/franchise-persistence.service';
import { UpdateFranchiseType } from '../franchises/schemas/update-franchise.schema';
import { PrismaService } from '../database/prisma.service';
import { BrowserPoolService } from './browser/browser-pool.service';
import { SitemapParserService } from './sitemap/sitemap-parser.service';
import {
  extractFranchiseImagesNewLayout,
  extractFranchiseImagesOldLayout,
  hasValidFranchiseImages,
} from './utils/franchise-image-extraction.util';

export interface FranchiseImagesSyncResult {
  processed: number;
  updated: number;
  skipped: number;
  errors: Array<{ franchiseId: string; scrapedWebsite: string; error: string }>;
}

@Injectable()
export class FranchiseImagesBackfillService {
  private readonly logger = new Logger(FranchiseImagesBackfillService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly browserPool: BrowserPoolService,
    private readonly sitemapParser: SitemapParserService,
    private readonly imageProcessor: ImageProcessorService,
    private readonly persistence: FranchisePersistenceService,
  ) {}

  /**
   * Dispara o backfill em background. Chamar de main.ts apos app.listen()
   * para a API ficar alcancavel enquanto o job roda.
   */
  scheduleStartupImageBackfill(): void {
    if (
      process.env.NODE_ENV === 'test' ||
      process.env.DISABLE_IMAGE_BACKFILL === '1'
    ) {
      this.logger.log(
        'Backfill de imagens no startup desativado (test ou DISABLE_IMAGE_BACKFILL).',
      );
      return;
    }

    const sentinelKey =
      process.env.IMAGE_BACKFILL_SENTINEL_SLUG?.trim() ||
      process.env.IMAGE_BACKFILL_SENTINEL_SKU?.trim();
    if (!sentinelKey) {
      this.logger.log(
        'IMAGE_BACKFILL_SENTINEL_SLUG (ou legado IMAGE_BACKFILL_SENTINEL_SKU) nao definido — backfill de imagens no startup desativado.',
      );
      return;
    }

    void this.runStartupImageBackfill(sentinelKey).catch((e) => {
      this.logger.error(
        'Falha no backfill de imagens no startup',
        e instanceof Error ? e.stack : e,
      );
    });
  }

  private async runStartupImageBackfill(sentinelKey: string): Promise<void> {
    const sentinel = await this.findSentinelFranchise(sentinelKey);

    if (!sentinel) {
      this.logger.warn(
        `Franquia sentinela nao encontrada (slug="${sentinelKey}") — backfill de imagens no startup ignorado.`,
      );
      return;
    }

    if (hasValidFranchiseImages(sentinel)) {
      this.logger.log(
        `Franquia sentinela (slug=${sentinelKey}, id=${sentinel.id}) ja possui imagens validas — backfill de imagens no startup ignorado.`,
      );
      return;
    }

    this.logger.log(
      'Iniciando backfill de imagens (background): sentinela sem midia valida.',
    );
    const result = await this.syncFranchiseImagesFromPortal({ concurrency: 3 });
    this.logger.log(
      `Backfill de imagens (background) concluido: processed=${result.processed} updated=${result.updated} skipped=${result.skipped} errors=${result.errors.length}`,
    );
  }

  private async findSentinelFranchise(slug: string) {
    return this.prisma.franchise.findFirst({
      where: { slug },
    });
  }

  /**
   * Sincroniza logo/thumbnail/galeria a partir do portal (Cheerio + Puppeteer, sem LLM).
   * Nao usa ensureScrapingEnabled.
   *
   * URLs salvas no banco vêm de {@link ImageProcessorService.processImageUrls} →
   * {@link DownloadService.downloadImage}, que usa env `BASE_URL` (não hardcode).
   */
  async syncFranchiseImagesFromPortal(options?: {
    concurrency?: number;
    franchiseIds?: string[];
    /** Se true, reprocessa todas com scrapedWebsite mesmo ja tendo imagens */
    force?: boolean;
  }): Promise<FranchiseImagesSyncResult> {
    const concurrency = Math.max(1, options?.concurrency ?? 3);

    const where =
      options?.franchiseIds && options.franchiseIds.length > 0
        ? {
            id: { in: options.franchiseIds },
            scrapedWebsite: { not: null },
          }
        : { scrapedWebsite: { not: null } };

    const rows = await this.prisma.franchise.findMany({
      where,
      select: {
        id: true,
        scrapedWebsite: true,
        logoUrl: true,
        thumbnailUrl: true,
        galleryUrls: true,
      },
    });

    const candidates = rows.filter((r) => {
      if (!r.scrapedWebsite) {
        return false;
      }
      if (options?.force) {
        return true;
      }
      return !hasValidFranchiseImages({
        logoUrl: r.logoUrl,
        thumbnailUrl: r.thumbnailUrl,
        galleryUrls: r.galleryUrls,
      });
    });

    let skippedCount = rows.length - candidates.length;

    const result: FranchiseImagesSyncResult = {
      processed: 0,
      updated: 0,
      skipped: 0,
      errors: [],
    };

    for (let i = 0; i < candidates.length; i += concurrency) {
      const chunk = candidates.slice(i, i + concurrency);
      await Promise.all(
        chunk.map(async (franchise) => {
          const url = franchise.scrapedWebsite as string;
          result.processed++;
          try {
            const html = await this.fetchPageContent(url);
            const $ = cheerio.load(html);
            const pageType =
              await this.sitemapParser.detectSinglePageType(url);

            const extracted =
              pageType === 'franchise-new'
                ? extractFranchiseImagesNewLayout($)
                : extractFranchiseImagesOldLayout($);

            const hasNewFromPage =
              !!extracted.logoUrl ||
              !!extracted.thumbnailUrl ||
              !!extracted.galleryUrls;
            if (!hasNewFromPage) {
              skippedCount++;
              this.logger.debug(
                `Nenhuma imagem extraida do HTML para ${franchise.id}`,
              );
              return;
            }

            // Mesclar com o que ja existe no banco para nao apagar campos nao extraidos
            // (updateRecordByScrapedWebsite remove arquivos antigos antes do update).
            const record: UpdateFranchiseType = {
              scrapedWebsite: url,
              logoUrl: extracted.logoUrl ?? franchise.logoUrl ?? undefined,
              thumbnailUrl:
                extracted.thumbnailUrl ?? franchise.thumbnailUrl ?? undefined,
              galleryUrls:
                extracted.galleryUrls ?? franchise.galleryUrls ?? undefined,
              lastScrapedAt: new Date(),
            };

            const { processedRecords } =
              await this.imageProcessor.processImageUrls<UpdateFranchiseType>(
                [record],
                'franchises',
              );

            const finalRecord = processedRecords[0];
            if (!finalRecord?.scrapedWebsite) {
              throw new Error('Record sem scrapedWebsite apos processamento');
            }

            await this.persistence.updateRecordByScrapedWebsite(
              finalRecord.scrapedWebsite,
              finalRecord,
            );
            result.updated++;
          } catch (err) {
            result.errors.push({
              franchiseId: franchise.id,
              scrapedWebsite: url,
              error: err instanceof Error ? err.message : String(err),
            });
            this.logger.warn(
              `Backfill imagens falhou para ${franchise.id} (${url}): ${result.errors[result.errors.length - 1].error}`,
            );
          }
        }),
      );
    }

    result.skipped = skippedCount;
    return result;
  }

  private async fetchPageContent(url: string): Promise<string> {
    return this.browserPool.withPage(async (page) => {
      await page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
      );

      page.setDefaultNavigationTimeout(45_000);
      page.setDefaultTimeout(45_000);

      try {
        await page.goto(url, { waitUntil: 'domcontentloaded' });
      } catch (err) {
        this.logger.warn(
          `Primeira navegacao falhou: ${(err as Error).message}`,
        );
        await page.goto(url, { waitUntil: 'networkidle2' });
      }

      await new Promise((resolve) => setTimeout(resolve, 1500));

      return page.content();
    });
  }
}
