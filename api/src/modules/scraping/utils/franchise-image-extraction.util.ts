import * as cheerio from 'cheerio';

export interface ExtractedFranchiseImages {
  logoUrl: string | null;
  thumbnailUrl: string | null;
  galleryUrls: string | null;
}

/**
 * Layout "franchise-new" (Portal do Franchising) — só imagens, sem vídeo/LLM.
 */
export function extractFranchiseImagesNewLayout(
  $: cheerio.CheerioAPI,
): ExtractedFranchiseImages {
  const logoRaw = $('div.logo-photo img').attr('data-src');
  const logoUrl = logoRaw?.trim() ? logoRaw.trim() : null;

  const thumbRaw = $('img[class*="main-img lazyloading"]').attr('src');
  const thumbnailUrl = thumbRaw?.trim() ? thumbRaw.trim() : null;

  const galleryUrls: string[] = [];
  const carousel = $('div[class*="carousel-cell"]');
  let current = carousel.next();
  while (current.length) {
    current.find('img').each((_, el) => {
      const src = $(el).attr('src');
      if (src && !galleryUrls.includes(src)) {
        galleryUrls.push(src);
      }
    });
    current = current.next();
  }

  return {
    logoUrl,
    thumbnailUrl,
    galleryUrls:
      galleryUrls.length > 0 ? JSON.stringify(galleryUrls) : null,
  };
}

/**
 * Layout "franchise-old" — sem thumbnail no HTML atual.
 */
export function extractFranchiseImagesOldLayout(
  $: cheerio.CheerioAPI,
): ExtractedFranchiseImages {
  const logoRaw = $('img[class*="logo-non-advertiser"]').attr('src');
  const logoUrl = logoRaw?.trim() ? logoRaw.trim() : null;

  const galleryUrls: string[] = [];
  const startHeading = $('h3:contains("Sobre a franquia")').first();
  if (startHeading.length > 0) {
    const endHeading = startHeading
      .nextAll('div[class*="container-salmon"]')
      .first();
    let current = startHeading.next();
    while (
      current.length &&
      (endHeading.length === 0 || !current.is(endHeading))
    ) {
      current.find('img').each((_, el) => {
        const src = $(el).attr('src');
        if (src && !galleryUrls.includes(src)) {
          galleryUrls.push(src);
        }
      });
      current = current.next();
    }
  }

  return {
    logoUrl,
    thumbnailUrl: null,
    galleryUrls:
      galleryUrls.length > 0 ? JSON.stringify(galleryUrls) : null,
  };
}

export type FranchiseImageFields = {
  logoUrl?: string | null;
  thumbnailUrl?: string | null;
  galleryUrls?: string | null;
};

/**
 * Considera que já há mídia persistida quando há logo, banner ou galeria com pelo menos uma URL/path.
 * Lista JSON vazia `[]` não conta como válida.
 */
export function hasValidFranchiseImages(f: FranchiseImageFields): boolean {
  if (f.logoUrl?.trim()) {
    return true;
  }
  if (f.thumbnailUrl?.trim()) {
    return true;
  }
  const raw = f.galleryUrls?.trim();
  if (!raw) {
    return false;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed.some(
        (x) => typeof x === 'string' && x.trim().length > 0,
      );
    }
  } catch {
    return raw.length > 0;
  }
  return false;
}
