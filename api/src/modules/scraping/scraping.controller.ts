import { Body, Controller, Param, Patch, Post, UseGuards } from '@nestjs/common';
import {
  ApiBearerAuth,
  ApiBody,
  ApiOperation,
  ApiParam,
  ApiResponse,
  ApiTags,
} from '@nestjs/swagger';
import { Role } from '@prisma/client';
import { Roles } from '../auth/decorators/roles.decorator';
import { JwtGuard } from '../auth/guards/jwt.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { SyncFranchiseImagesBodyDto } from './dto/sync-franchise-images.dto';
import { ScrapingService } from './scraping.service';

@ApiTags('scraping')
@Controller('scraping')
@UseGuards(JwtGuard, RolesGuard)
@ApiBearerAuth()
export class ScrapingController {
  constructor(private readonly scrapingService: ScrapingService) {}

  @Roles(Role.ADMIN)
  @Patch(':id')
  @ApiOperation({ summary: 'Update franchise by scraping (admin only)' })
  @ApiParam({ name: 'id', description: 'Franchise ID' })
  @ApiResponse({ status: 200, description: 'Franchise updated successfully' })
  @ApiResponse({ status: 403, description: 'Forbidden - Admin only' })
  async updateFranchiseById(@Param('id') id: string) {
    return await this.scrapingService.updateFranchiseById(id);
  }

  @Roles(Role.ADMIN)
  @Post('franchises/images/sync')
  @ApiOperation({
    summary:
      'Backfill de imagens (logo/thumbnail/galeria) via portal, sem LLM — pode ser pesado',
  })
  @ApiBody({ type: SyncFranchiseImagesBodyDto, required: false })
  @ApiResponse({ status: 200, description: 'Resumo do processamento' })
  async syncFranchiseImages(@Body() body: SyncFranchiseImagesBodyDto) {
    return this.scrapingService.syncFranchiseImagesFromPortal({
      franchiseIds: body?.franchiseIds,
      force: body?.force,
      concurrency: body?.concurrency,
    });
  }
}
