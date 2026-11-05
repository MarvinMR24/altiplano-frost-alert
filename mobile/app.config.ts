// Expo app config (replaces app.json so values can come from the environment).
// No secrets here: the Google Maps key is read from GOOGLE_MAPS_API_KEY, which is an
// EAS environment variable for builds (see docs/android_build.md). A Maps key always ends up
// inside the APK, so it must be restricted to this package and signing certificate in Google
// Cloud.
import type { ConfigContext, ExpoConfig } from 'expo/config';

const ANDROID_PACKAGE = 'com.marvinmr24.frostwatch';
const VERSION = '1.0.0';
// Increase for every APK or AAB you publish (Android refuses to update to an equal or lower code).
const ANDROID_VERSION_CODE = Number(process.env.ANDROID_VERSION_CODE ?? 1);

// Keep only the key itself: a value pasted in a terminal can carry invisible characters
// (bracketed paste codes, a newline) that break the generated AndroidManifest.xml.
function cleanMapsKey(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  const match = raw.match(/AIza[0-9A-Za-z_-]{35}/);
  if (match) return match[0];
  const trimmed = raw.replace(/[^\x21-\x7E]/g, '');
  return trimmed || undefined;
}

const googleMapsKey = cleanMapsKey(process.env.GOOGLE_MAPS_API_KEY);
// EAS project id (not a secret). Paste the id printed by `npx eas-cli init` here: EAS build
// servers do not receive mobile/.env.local, so the id must live in this file (an
// EAS_PROJECT_ID environment variable overrides it).
const EAS_PROJECT_ID_FROM_INIT = 'eafa6b61-46c3-4276-8303-52af9c5fdd98';
// Expo account that owns the EAS project (@snarf3/frostwatch-altiplano).
const EAS_OWNER = 'snarf3';
const easProjectId =
  process.env.EAS_PROJECT_ID || process.env.EXPO_PUBLIC_EAS_PROJECT_ID || EAS_PROJECT_ID_FROM_INIT || undefined;

if (!googleMapsKey && process.env.EAS_BUILD_PLATFORM === 'android') {
  console.warn(
    '[app.config] GOOGLE_MAPS_API_KEY is not set: the Android build will show an empty map. ' +
      'Create it as an EAS environment variable (docs/android_build.md).',
  );
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'FrostWatch',
  slug: 'frostwatch-altiplano',
  owner: EAS_OWNER,
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
    // Release builds are minified with R8. Room (used by WorkManager, pulled in by
    // react-native-maps) finds its generated *_Impl database classes by reflection; without
    // these rules R8 strips them and the app crashes at start with
    // "Failed to create an instance of class androidx.work.impl.WorkDatabase".
    [
      'expo-build-properties',
      {
        android: {
          extraProguardRules: [
            '-keep class * extends androidx.room.RoomDatabase { <init>(); }',
            '-keep class androidx.work.impl.WorkDatabase_Impl { *; }',
          ].join('\n'),
        },
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
