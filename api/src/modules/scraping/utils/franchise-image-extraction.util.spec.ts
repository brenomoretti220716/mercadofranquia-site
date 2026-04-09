import * as cheerio from 'cheerio';
import {
  extractFranchiseImagesNewLayout,
  extractFranchiseImagesOldLayout,
  hasValidFranchiseImages,
} from './franchise-image-extraction.util';

describe('franchise-image-extraction.util', () => {
  describe('hasValidFranchiseImages', () => {
    it('returns false for empty gallery JSON array', () => {
      expect(
        hasValidFranchiseImages({
          galleryUrls: '[]',
        }),
      ).toBe(false);
    });

    it('returns true when logoUrl is non-empty', () => {
      expect(
        hasValidFranchiseImages({
          logoUrl: '/uploads/franchises/x.png',
        }),
      ).toBe(true);
    });

    it('returns true when gallery has at least one URL', () => {
      expect(
        hasValidFranchiseImages({
          galleryUrls: JSON.stringify(['https://example.com/a.jpg']),
        }),
      ).toBe(true);
    });
  });

  describe('extractFranchiseImagesNewLayout', () => {
    it('reads logo data-src and thumbnail src', () => {
      const html = `
        <div class="logo-photo"><img data-src="https://cdn/logo.png" /></div>
        <img class="main-img lazyloading x" src="https://cdn/banner.jpg" />
        <div class="carousel-cell"></div>
        <div><img src="https://cdn/g1.jpg"/></div>
      `;
      const $ = cheerio.load(html);
      const r = extractFranchiseImagesNewLayout($);
      expect(r.logoUrl).toBe('https://cdn/logo.png');
      expect(r.thumbnailUrl).toBe('https://cdn/banner.jpg');
      expect(r.galleryUrls).toContain('g1.jpg');
    });
  });

  describe('extractFranchiseImagesOldLayout', () => {
    it('reads logo and gallery between headings', () => {
      const html = `
        <h3>Sobre a franquia</h3>
        <div><img src="https://old/g1.png"/></div>
        <div class="container-salmon"></div>
        <img class="logo-non-advertiser x" src="https://old/logo.png" />
      `;
      const $ = cheerio.load(html);
      const r = extractFranchiseImagesOldLayout($);
      expect(r.logoUrl).toBe('https://old/logo.png');
      expect(r.thumbnailUrl).toBeNull();
      expect(r.galleryUrls).toContain('g1.png');
    });
  });
});
