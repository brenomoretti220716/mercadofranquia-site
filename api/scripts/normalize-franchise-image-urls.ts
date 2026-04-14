import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();
const LEGACY_HOSTS = new Set(['franchising.com', 'www.franchising.com']);

function getBaseOriginFromEnv(): string {
  const baseUrl = process.env.BASE_URL;

  if (!baseUrl) {
    throw new Error('BASE_URL is required to normalize franchise image URLs.');
  }

  return new URL(baseUrl).origin;
}

function rewriteUrl(value: string, targetOrigin: string): string {
  try {
    const parsed = new URL(value);

    if (!LEGACY_HOSTS.has(parsed.hostname)) {
      return value;
    }

    const target = new URL(targetOrigin);
    parsed.protocol = target.protocol;
    parsed.host = target.host;

    return parsed.toString();
  } catch {
    return value;
  }
}

function normalizeGalleryUrls(
  galleryUrls: string | null,
  targetOrigin: string,
): { value: string | null; changed: number } {
  if (!galleryUrls) {
    return { value: null, changed: 0 };
  }

  try {
    const parsed = JSON.parse(galleryUrls) as unknown;
    if (!Array.isArray(parsed)) {
      return { value: galleryUrls, changed: 0 };
    }

    let changed = 0;
    const normalized = parsed.map((item) => {
      if (typeof item !== 'string') {
        return item;
      }

      const rewritten = rewriteUrl(item, targetOrigin);
      if (rewritten !== item) {
        changed += 1;
      }

      return rewritten;
    });

    return {
      value: changed > 0 ? JSON.stringify(normalized) : galleryUrls,
      changed,
    };
  } catch {
    return { value: galleryUrls, changed: 0 };
  }
}

async function main() {
  const targetOrigin = getBaseOriginFromEnv();

  console.log(
    `Starting franchise image URL normalization using BASE_URL origin: ${targetOrigin}`,
  );

  const franchises = await prisma.franchise.findMany({
    where: {
      OR: [
        { logoUrl: { contains: 'franchising.com' } },
        { thumbnailUrl: { contains: 'franchising.com' } },
        { galleryUrls: { contains: 'franchising.com' } },
      ],
    },
    select: {
      id: true,
      name: true,
      logoUrl: true,
      thumbnailUrl: true,
      galleryUrls: true,
    },
  });

  if (franchises.length === 0) {
    console.log('No franchises found with legacy image host.');
    return;
  }

  let franchisesUpdated = 0;
  let urlsUpdated = 0;

  for (const franchise of franchises) {
    const nextLogoUrl = franchise.logoUrl
      ? rewriteUrl(franchise.logoUrl, targetOrigin)
      : null;
    const nextThumbnailUrl = franchise.thumbnailUrl
      ? rewriteUrl(franchise.thumbnailUrl, targetOrigin)
      : null;
    const nextGallery = normalizeGalleryUrls(franchise.galleryUrls, targetOrigin);

    const changedLogo = nextLogoUrl !== franchise.logoUrl;
    const changedThumbnail = nextThumbnailUrl !== franchise.thumbnailUrl;
    const changedGallery = nextGallery.value !== franchise.galleryUrls;

    if (!changedLogo && !changedThumbnail && !changedGallery) {
      continue;
    }

    await prisma.franchise.update({
      where: { id: franchise.id },
      data: {
        logoUrl: nextLogoUrl,
        thumbnailUrl: nextThumbnailUrl,
        galleryUrls: nextGallery.value,
      },
    });

    franchisesUpdated += 1;
    urlsUpdated += (changedLogo ? 1 : 0) + (changedThumbnail ? 1 : 0) + nextGallery.changed;

    console.log(`Updated franchise ${franchise.id} (${franchise.name}).`);
  }

  console.log('Normalization completed.');
  console.log(`Franchises updated: ${franchisesUpdated}`);
  console.log(`Image URLs updated: ${urlsUpdated}`);
}

void main()
  .catch((error) => {
    console.error('Failed to normalize franchise image URLs:', error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
