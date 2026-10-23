import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('ESLint and typescript-eslint CI configuration', () => {
  it('defines valid eslint.config.mjs with strict promise safety rules', async () => {
    const configPath = path.resolve(process.cwd(), 'eslint.config.mjs');
    expect(fs.existsSync(configPath)).toBe(true);

    const configModule = await import(configPath);
    const config = configModule.default;

    expect(Array.isArray(config)).toBe(true);
    expect(config.length).toBeGreaterThanOrEqual(3);

    // 1. Ignores check
    const ignoresObj = config.find((item: any) => item.ignores);
    expect(ignoresObj).toBeDefined();
    expect(ignoresObj.ignores).toContain('dist/**');
    expect(ignoresObj.ignores).toContain('node_modules/**');

    // 2. TypeScript rules check
    const tsConfig = config.find((item: any) =>
      item.files && item.files.includes('src/**/*.ts')
    );
    expect(tsConfig).toBeDefined();
    expect(tsConfig.plugins).toHaveProperty('@typescript-eslint');
    expect(tsConfig.rules['@typescript-eslint/no-floating-promises']).toBe('error');
    expect(tsConfig.rules['@typescript-eslint/no-misused-promises']).toBe('error');

    // 3. Tests override check
    const testOverride = config.find((item: any) =>
      item.files && item.files.includes('tests/**/*.ts') && item.rules && item.rules['@typescript-eslint/no-explicit-any'] === 'off'
    );
    expect(testOverride).toBeDefined();
  });

  it('declares lint and lint:fix scripts in package.json', () => {
    const pkg = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), 'package.json'), 'utf-8'));
    expect(pkg.scripts).toHaveProperty('lint');
    expect(pkg.scripts.lint).toBe('eslint .');
    expect(pkg.scripts).toHaveProperty('lint:fix');
    expect(pkg.scripts['lint:fix']).toBe('eslint . --fix');
    expect(pkg.devDependencies).toHaveProperty('eslint');
    expect(pkg.devDependencies).toHaveProperty('@typescript-eslint/eslint-plugin');
    expect(pkg.devDependencies).toHaveProperty('@typescript-eslint/parser');
  });

  it('includes pnpm lint step in ci.yml workflow', () => {
    const ciContent = fs.readFileSync(path.resolve(process.cwd(), '.github/workflows/ci.yml'), 'utf-8');
    expect(ciContent).toContain('- run: pnpm lint');
  });
});
