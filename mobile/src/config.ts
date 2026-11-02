// Runtime configuration from EXPO_PUBLIC_* variables (bundled into the app, never secrets).

const rawUrl = process.env.EXPO_PUBLIC_API_URL ?? '';

export const API_URL = rawUrl.replace(/\/+$/, '');

// Mock mode is the default so the app works offline without a backend.
export const USE_MOCK = (process.env.EXPO_PUBLIC_USE_MOCK ?? '1') !== '0' || API_URL === '';

export const EAS_PROJECT_ID = process.env.EXPO_PUBLIC_EAS_PROJECT_ID || undefined;
