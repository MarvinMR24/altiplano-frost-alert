// Runtime configuration from EXPO_PUBLIC_* variables (bundled into the app, never secrets).
import Constants from 'expo-constants';

const rawUrl = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/+$/, '');

// In development the laptop IP changes with the Wi-Fi network. When the configured backend
// is on a local address, use the host the phone already reaches Metro on (Expo Go's
// hostUri), keeping the configured port. Public URLs are left untouched.
const LOCAL_HOST = /^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+)$/;

function resolveApiUrl(url: string): string {
  if (!__DEV__ || !url) return url;
  const metroHost = Constants.expoConfig?.hostUri?.split(':')[0];
  if (!metroHost || !LOCAL_HOST.test(metroHost)) return url;
  const match = url.match(/^(https?:\/\/)([^/:]+)(:\d+)?(.*)$/);
  if (!match || !LOCAL_HOST.test(match[2])) return url;
  const [, scheme, , port = '', rest] = match;
  return `${scheme}${metroHost}${port}${rest}`;
}

export const API_URL = resolveApiUrl(rawUrl);

// Mock mode is the default so the app works offline without a backend.
export const USE_MOCK = (process.env.EXPO_PUBLIC_USE_MOCK ?? '1') !== '0' || API_URL === '';

export const EAS_PROJECT_ID = process.env.EXPO_PUBLIC_EAS_PROJECT_ID || undefined;
