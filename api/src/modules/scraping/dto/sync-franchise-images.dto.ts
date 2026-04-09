import { ApiPropertyOptional } from '@nestjs/swagger';

export class SyncFranchiseImagesBodyDto {
  @ApiPropertyOptional({
    description:
      'IDs de franquias a processar (default: todas com scrapedWebsite)',
    type: [String],
  })
  franchiseIds?: string[];

  @ApiPropertyOptional({
    description:
      'Se true, reprocessa mesmo quando ja existem imagens (operacao pesada)',
  })
  force?: boolean;

  @ApiPropertyOptional({ description: 'Concorrencia de paginas (default 3)' })
  concurrency?: number;
}
