// Expo app config (replaces app.json so values can come from the environment).
// No secrets here: the Google Maps key is read from GOOGLE_MAPS_ANDROID_API_KEY, which is an
// EAS environment variable for builds (see docs/android_build.md). A Maps key always ends up
// inside the APK, so it must be restricted to this package and signing certificate in Google
// Cloud.
import type { ConfigContext, ExpoConfig } from 'expo/config';

const ANDROID_PACKAGE = 'com.marvinmr24.frostwatch';
const VERSION = '1.0.0';
// Increase for every APK or AAB you publish (Android refuses to update to an equal or lower code).
const ANDROID_VERSION_CODE = Number(process.env.ANDROID_VERSION_CODE ?? 1);

const googleMapsKey = process.env.GOOGLE_MAPS_ANDROID_API_KEY;
// EAS project id (not a secret). Paste the id printed by `npx eas-cli init` here: EAS build
// servers do not receive mobile/.env.local, so the id must live in this file (an
// EAS_PROJECT_ID environment variable overrides it).
const EAS_PROJECT_ID_FROM_INIT = '';
const easProjectId =
  process.env.EAS_PROJECT_ID || process.env.EXPO_PUBLIC_EAS_PROJECT_ID || EAS_PROJECT_ID_FROM_INIT || undefined;

if (!googleMapsKey && process.env.EAS_BUILD_PLATFORM === 'android') {
  console.warn(
    '[app.config] GOOGLE_MAPS_ANDROID_API_KEY is not set: the Android build will show an empty map. ' +
      'Create it as an EAS environment variable (docs/android_build.md).',
  );
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'FrostWatch',
  slug: 'frostwatch-altiplano',
  scheme: 'frostwatch',
  version: VERSION,
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'light',
  ios: {
    supportsTablet: false,
  },
  android: {
    package: ANDROID_PACKAGE,
    versionCode: ANDROID_VERSION_CODE,
    adaptiveIcon: {
      backgroundColor: '#F4EDE1',
      foregroundImage: './assets/android-icon-foreground.png',
      backgroundImage: './assets/android-icon-background.png',
      monochromeImage: './assets/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
    // Release builds block plain http (no usesCleartextTraffic): the API must be https.
    ...(googleMapsKey ? { config: { googleMaps: { apiKey: googleMapsKey } } } : {}),
  },
  web: {
    favicon: './assets/favicon.png',
  },
  plugins: [
    'expo-router',
    'expo-status-bar',
    'expo-secure-store',
    'expo-localization',
    'expo-web-browser',
    // SDK 58 configures the splash screen through this plugin (was the "splash" field).
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 200,
        resizeMode: 'contain',
        backgroundColor: '#F4EDE1',
      },
    ],
    [
      'expo-location',
      {
        locationWhenInUsePermission: 'FrostWatch uses your location only to move the map to where you are.',
      },
    ],
  ],
  extra: {
    ...config.extra,
    ...(easProjectId ? { eas: { projectId: easProjectId } } : {}),
  },
});
