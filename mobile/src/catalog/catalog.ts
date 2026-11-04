// Shared catalog shapes. Labels in ay/qu exist only where the name is well known;
// otherwise labels fall back to Spanish at runtime (see labelFor).

export type CropCategory = 'tuber' | 'grain' | 'legume' | 'vegetable' | 'forage' | 'greenhouse';

export interface CatalogLabels {
  es: string;
  en: string;
  ay?: string;
  qu?: string;
}

export interface CatalogItem {
  id: string;
  category: CropCategory | 'livestock';
  labels: CatalogLabels;
  synonyms: string[];
  icon: string;
}

export type Language = 'es' | 'en' | 'ay' | 'qu';

export function labelFor(item: CatalogItem, language: Language): string {
  return item.labels[language] ?? item.labels.es;
}

export function normalizeQuery(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function itemMatches(item: CatalogItem, query: string, language: Language): boolean {
  const q = normalizeQuery(query);
  if (!q) return true;
  const haystacks = [labelFor(item, language), item.labels.es, ...item.synonyms].map(normalizeQuery);
  return haystacks.some((h) => h.includes(q));
}
