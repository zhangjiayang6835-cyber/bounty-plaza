import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Website accessibility and motion-preference audit', () => {
  it('validates document landmarks, skip-link, and heading hierarchy in index.html', () => {
    const htmlPath = path.resolve(process.cwd(), 'website/index.html');
    expect(fs.existsSync(htmlPath)).toBe(true);

    const html = fs.readFileSync(htmlPath, 'utf-8');

    // 1. Skip link
    expect(html).toContain('class="skip-link"');
    expect(html).toContain('href="#main-content"');

    // 2. Landmarks
    expect(html).toContain('<main id="main-content"');
    expect(html).toContain('<nav aria-label="Primary"');

    // 3. Single logical H1 inside main
    const h1Matches = html.match(/<h1[^>]*>/g);
    expect(h1Matches).not.toBeNull();
    expect(h1Matches?.length).toBe(1);

    // 4. Flow node H3 stage labels
    expect(html).toContain('<h3 class="stage-label">Burn</h3>');
    expect(html).toContain('<h3 class="stage-label">Attest</h3>');
    expect(html).toContain('<h3 class="stage-label">Mint</h3>');

    // 5. Screen reader text on external links
    expect(html).toContain('class="sr-only"');
    expect(html).toContain('(opens in a new tab)');
  });

  it('validates prefers-reduced-motion handling in hero-animation.ts and animations.ts', () => {
    const heroAnimPath = path.resolve(process.cwd(), 'website/src/hero-animation.ts');
    expect(fs.existsSync(heroAnimPath)).toBe(true);
    const heroContent = fs.readFileSync(heroAnimPath, 'utf-8');

    expect(heroContent).toContain('prefers-reduced-motion: reduce');
    expect(heroContent).toContain('drawStatic');

    const animPath = path.resolve(process.cwd(), 'website/src/animations.ts');
    expect(fs.existsSync(animPath)).toBe(true);
    const animContent = fs.readFileSync(animPath, 'utf-8');
    expect(animContent).toContain('prefers-reduced-motion: reduce');
  });

  it('validates high-contrast focus-visible styles and reduced motion in style.css', () => {
    const cssPath = path.resolve(process.cwd(), 'website/src/style.css');
    expect(fs.existsSync(cssPath)).toBe(true);
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

    // High contrast focus indicator
    expect(cssContent).toContain(':focus-visible');
    expect(cssContent).toContain('outline');

    // Reduced motion media query
    expect(cssContent).toContain('@media (prefers-reduced-motion: reduce)');
    expect(cssContent).toContain('scroll-behavior: auto');
  });
});
