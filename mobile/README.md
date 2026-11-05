# mobile (module 3)

Expo (SDK 58), React Native, TypeScript and Expo Router, for Expo Go on an iPhone. No
development build and no custom native modules. Talks to the backend only through the HTTP
API in `docs/api_contract.md`. The app is not containerized: it always runs on the host.

Test plan:
1. Now: local testing in the browser (Expo web) against the backend on `localhost:8000`.
2. Next: Expo Go on the iPhone on the same Wi-Fi against the backend on the Mac
   (`http://<Mac IP>:8000`, no cloud). See below.


Quick start: copy `.env.example` to `.env.local` (it points to the hackathon AWS backend until
2026-11-16; for a local backend use your computer's Wi-Fi address), then `npm install` and
`npx expo start -c`. Full guide and limitations: "Try it and run it" in the root README.

## Run on the web (local testing)

```
cd mobile
npm install
npx expo start --web   # opens http://localhost:8081
```

For a production bundle check (closer to real speed than the dev bundle):

```
npx expo start --web --no-dev --minify
```

Differences on the web build (local testing only, not a shipped web version):
- Maps: `src/ui/maps.web.tsx` wraps Leaflet with a real base map (standard
  OpenStreetMap tiles, no API key, with attribution and zoom control) and supports what the screens
  use: coverage polygons, level markers, zones, draggable vertices, map taps and
  `animateToRegion`. The iPhone uses `src/ui/maps.tsx` (react-native-maps, Apple Maps,
  `mutedStandard`, no POIs, no rotation or pitch). Screens import from `@/ui/maps`.
- Session: stored in `localStorage` (`src/auth/session.web.ts`) instead of SecureStore.
- Push: not available in the browser. Email alerts and the in-app History still work.
- The backend allows the Expo web origin through CORS (`CORS_ORIGINS`, default
  `http://localhost:8081,http://127.0.0.1:8081`).

## Run on the iPhone on the same Wi-Fi (no cloud)

The backend runs with `docker compose up` at the repo root and publishes port 8000 on
all interfaces of the Mac (`ports: ["8000:8000"]` in `docker-compose.yml`), so a phone
on the same Wi-Fi can reach it directly.

1. Start the backend: `docker compose up` at the repo root.
2. Get the Mac IP: `ipconfig getifaddr en0`.
3. Create `mobile/.env.local` (gitignored) from `mobile/.env.example` with:
   `EXPO_PUBLIC_API_URL=http://<that IP>:8000` and `EXPO_PUBLIC_USE_MOCK=0`.
4. On the phone, open Safari and test `http://<that IP>:8000/health` first. It must
   return `{"status": "ok"}`.
5. Run `npx expo start` (LAN) in `mobile/`, scan the QR with the iPhone Camera app
   and open it in Expo Go. If the macOS firewall asks, allow incoming connections.
6. If the guest Wi-Fi or a VPN blocks the LAN, use `npx expo start --tunnel`.
7. If you also want the web build from the phone browser, add `http://<that IP>:8081`
   to `CORS_ORIGINS` in the root `.env` (for example
   `CORS_ORIGINS=http://localhost:8081,http://127.0.0.1:8081,http://<that IP>:8081`)
   and restart the backend.

Push in Expo Go needs an EAS project id. Two options (run one yourself, they write the
same value):
- `npx eas-cli init` in `mobile/` and put the id in `EAS_PROJECT_ID` (`app.config.ts` reads it), or
- set `EXPO_PUBLIC_EAS_PROJECT_ID` in `mobile/.env.local`.

## Configuration

Create `mobile/.env.local` (gitignored) from `mobile/.env.example`:

| Variable | Meaning |
|---|---|
| `EXPO_PUBLIC_USE_MOCK` | `1` (default): offline mock data with a permanent "MOCK DATA" banner. `0`: real backend. |
| `EXPO_PUBLIC_API_URL` | Backend base URL: `http://localhost:8000` for web testing, `http://<Mac IP>:8000` for the iPhone on the same Wi-Fi. Empty forces mock mode. |
| `EXPO_PUBLIC_EAS_PROJECT_ID` | Optional EAS project id for Expo push tokens (or set `EAS_PROJECT_ID` after `npx eas-cli init`; `app.config.ts` reads it). |

`EXPO_PUBLIC_*` values are bundled into the app: never put secrets there. Restart
`npx expo start` after changing them.

Pointing at the backend:
- Web, local: `docker compose up` at the repo root (backend only), then
  `EXPO_PUBLIC_API_URL=http://localhost:8000` and `EXPO_PUBLIC_USE_MOCK=0`.
- iPhone, same Wi-Fi: `EXPO_PUBLIC_API_URL=http://<Mac IP>:8000` and
  `EXPO_PUBLIC_USE_MOCK=0` (see steps above).

## Mock mode

Mock mode (`src/api/mock.ts`, `src/api/mockData.ts`) keeps users, passwords, AOIs and
read flags in memory, so the whole flow works offline: any email, any valid password, any
6-digit code. Every number in mock mode is arbitrary and flagged as mock.

## Notifications

- iPhone in Expo Go: push works once the app has an EAS project id (see above) and the user
  grants permission. Taps on a push with `data.alert_id` open the alert detail.
- Android in Expo Go: remote push is not available since SDK 53. The app skips push there
  and does not load `expo-notifications`, so it does not crash.

## Visual identity and logo

- Palette tokens live in `src/ui/theme.ts` (navy `#0F2A44` primary, beige background,
  red accents). No hex literals in screens or components.
- Level colors go from low to very_high without green and are always paired with text
  and an icon (`levelIcons` in the theme).
- Icons are custom (`src/ui/icons/`, `<Icon name="..." />`); Ionicons stays only for the
  Google brand glyph.
- The logo is a map pin (your place) holding a snowy Altiplano peak, a frost snowflake and
  a red alert dot, on a beige rounded square (`assets/logo.svg`,
  `assets/logo-horizontal.svg`, `assets/logo-mono.svg` with cut-outs for one-color system
  icons). It is rendered with `react-native-svg` as `Logo` in `src/ui/logo.tsx`;
  `node scripts/check-logo.mjs` checks that the SVG files use the same paths.
- PNG assets are generated from the SVGs with a dev-only script
  (`@resvg/resvg-js` devDependency, not bundled into the app):

```
node scripts/build-icons.mjs   # writes icon.png, splash-icon.png, favicon.png and Android adaptive icons (pin padded to the safe zone)
```

## Auth flow

Welcome (first screen) with language chips, 4-step sign up (about you, account with
password rules and strength meter, email code, profile), sign in with password or with a
code, forgot password (email, code, new password), change password in Profile. Password
policy: 8+ characters, one letter, one number. Sign in with Google (system browser and a
one-time ticket; active only when the backend has the Google settings, otherwise "coming
soon"); see `src/auth/providers.ts` and `docs/api_contract.md`. There is no Apple sign in.

## Android APK and app config

`app.config.ts` replaces `app.json` (same fields) so values come from the environment: the
Google Maps key (`GOOGLE_MAPS_API_KEY`, an EAS secret, never in the repo), the
Android `versionCode` (`ANDROID_VERSION_CODE`) and the EAS project id (`EAS_PROJECT_ID`).
Android builds use Google Maps (`PROVIDER_GOOGLE` in `src/ui/maps.tsx`), iOS keeps Apple
Maps, the web keeps Leaflet. Build profiles live in `eas.json`; the APK talks only to the
https backend. Full guide: `docs/android_build.md`.

## Map layers, place search and privacy

- Base map: satellite imagery with place names by default (`mapType="hybrid"`: Apple Maps
  on iOS, Google Maps on Android, both included in Expo Go without a key) and the street
  map (`mutedStandard` on iOS, `standard` on Android) through the round layers button.
  The choice is stored per device in AsyncStorage (`src/ui/mapLayer.ts`).
- Web build: Esri World Imagery plus the Esri World Boundaries and Places labels
  ("Imagery: Esri, Maxar, Earthstar Geographics and the GIS User Community"), max zoom 19
  with level 18 upscaled in rural areas, or OpenStreetMap tiles for the street map.
- Place search (`src/geo/search.ts`, tested in `scripts/unit-tests.mjs`): coverage cells
  first (offline), then Photon (komoot, OpenStreetMap data) limited to the coverage box,
  with Nominatim (OpenStreetMap) as fallback. Minimum 3 characters, 500 ms debounce, at
  most one request per second, in-memory cache, stale requests cancelled. Native requests
  send the User-Agent "FrostWatchAltiplano/1.0 (hackathon demo)".
- Privacy: search text goes to Photon or Nominatim and is not stored by the app. "My
  location" uses `expo-location` foreground permission only when tapped; the position only
  moves the camera and is never stored or sent to the backend.
- Rural imagery can be coarse or several years old; houses may look blurry at the closest
  zoom.

## Languages

`es` (default, source of keys), `en`, `ay` (Aymar aru), `qu` (Runa simi). ay/qu are
partial: missing keys fall back to Spanish, listed in `docs/i18n_review.md` for a native
speaker. Alert emails and explanations exist only in es/en; ay/qu users get Spanish.

## Layout

```
src/app/            routes (Expo Router): welcome, signup, login, verify, forgot, onboarding,
                    (tabs)/{index,zones,history,profile}, zones/draw, zones/[id], alerts/[id],
                    change-email, change-password
src/api/            client.ts (entry), http.ts, mock.ts, mockData.ts, types.ts
src/auth/           session (SecureStore; session.web.ts uses localStorage), AuthProvider, providers.ts (Google sign in)
src/i18n/           es.ts (default, source of keys), en.ts, ay.ts, qu.ts
src/catalog/        crops.ts (40+), livestock.ts (14), catalog.ts (labels, search)
src/date/           calendar.ts (pure month grid, tested)
src/geo/            point in polygon, centroid, circles; search.ts (place search providers)
src/notifications/  guarded push helpers
src/ui/             theme, logo, icons/, shared components, auth.tsx, CatalogPicker.tsx,
                    ThresholdField.tsx, NightPicker.tsx, maps.tsx (native) and maps.web.tsx (Leaflet web map),
                    mapLayer.ts, MapSearch.tsx, MapOverlay.tsx (pill, chip, round buttons), mapShapes.tsx,
                    motion.tsx, feedback.ts (haptics), SpeakButton.tsx, location.ts
```

Checks: `npx tsc --noEmit`, `npx expo export --platform web`, `node scripts/check-i18n.mjs`,
`node scripts/unit-tests.mjs`.
