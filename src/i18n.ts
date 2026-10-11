import en from './locales/en.json';
import uz from './locales/uz.json';

export type Locale = typeof en;

export const locales: Record<string, Locale> = {
  en,
  uz,
};

export const defaultLocale = 'en';

export function getLocale(lang: string): Locale {
  return locales[lang] ?? locales[defaultLocale];
}
