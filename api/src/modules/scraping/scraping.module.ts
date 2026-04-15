import { Module } from '@nestjs/common';
import { GuardsModule } from '../auth/guards/guards.module';
import { PrismaModule } from '../database/prisma.module';
import { FranchisesModule } from '../franchises/franchises.module';
import { BrowserPoolService } from './browser/browser-pool.service';
import { ScrapingSchedulerService } from './schedulers/scraping-scheduler.service';
import { FranchiseNewScraper } from './scrapers/franchise-new.scraper.service';
import { FranchiseOldScraper } from './scrapers/franchise-old.scraper.service';
import { FranchiseImagesBackfillService } from './franchise-images-backfill.service';
import { ScrapingController } from './scraping.controller';
import { ScrapingService } from './scraping.service';
import { SitemapParserService } from './sitemap/sitemap-parser.service';
import { SitemapReaderService } from './sitemap/sitemap-reader.service';
import { CsvGeneratorService } from './storage/csv-generator.service';

@Module({
  controllers: [ScrapingController],
  providers: [
    BrowserPoolService,
    SitemapReaderService,
    SitemapParserService,
    ScrapingService,
    FranchiseImagesBackfillService,
    ScrapingSchedulerService,
    FranchiseOldScraper,
    FranchiseNewScraper,
    CsvGeneratorService,
  ],
  exports: [ScrapingService],
  imports: [PrismaModule, FranchisesModule, GuardsModule],
})
export class ScrapingModule {}
