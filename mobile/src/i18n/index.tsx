import AsyncStorage from '@react-native-async-storage/async-storage';
import { getLocales } from 'expo-localization';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import type { Language } from '@/api/types';
import { en } from './en';
import { es, type TranslationKey } from './es';

export type { TranslationKey };

const DICTIONARIES: Record<Language, Record<TranslationKey, string>> = { es, en };
const STORAGE_KEY = 'frostwatch.language';
export const DEFAULT_LANGUAGE: Language = 'es';

type Params = Record<string, string | number>;

export function translate(language: Language, key: TranslationKey, params?: Params): string {
  const template = DICTIONARIES[language][key] ?? es[key] ?? key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

// Looks up an optional key (e.g. a feature name coming from the API) with a fallback.
export function translateOptional(language: Language, key: string, fallback: string): string {
  return (DICTIONARIES[language] as Record<string, string>)[key] ?? fallback;
}

interface I18nValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, params?: Params) => string;
  tOptional: (key: string, fallback: string) => string;
  formatDate: (isoDate: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((stored) => {
        if (stored === 'es' || stored === 'en') setLanguageState(stored);
      })
      .catch(() => undefined);
  }, []);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    AsyncStorage.setItem(STORAGE_KEY, next).catch(() => undefined);
  }, []);

  const value = useMemo<I18nValue>(() => {
    const region = getLocales()[0]?.regionCode ?? 'BO';
    const locale = `${language}-${region}`;
    return {
      language,
      setLanguage,
      t: (key, params) => translate(language, key, params),
      tOptional: (key, fallback) => translateOptional(language, key, fallback),
      formatDate: (isoDate) => formatNightDate(isoDate, locale),
    };
  }, [language, setLanguage]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error('useI18n must be used inside I18nProvider');
  return value;
}

// Night dates are calendar dates (YYYY-MM-DD); format them without timezone shifts.
function formatNightDate(isoDate: string, locale: string): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  if (!y || !m || !d) return isoDate;
  try {
    return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(locale, {
      timeZone: 'UTC',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoDate;
  }
}
