# mobile (module 3)

Expo (SDK 58), React Native, TypeScript and Expo Router, for Expo Go on an iPhone. No
development build and no custom native modules. Talks to the backend only through the HTTP
API in `docs/api_contract.md`. The app is not containerized: it always runs on the host.

Test plan:
1. Now: local testing in the browser (Expo web) against the backend on `localhost:8000`.
2. After the backend is deployed to AWS: the iPhone in Expo Go against the public AWS URL.

## Run on the web (local testing)

```
cd mobile
npm install
npx expo start --web   # opens http://localhost:8081
```

Differences on the web build (local testing only, not a shipped web version):
- Maps: `react-native-maps` has no web implementation, so `src/ui/maps.web.tsx` draws a
  schematic map (coverage circles, cells, zones and polygon drawing on a lat/lon grid, no base
  map, no pan or zoom). The iPhone uses `src/ui/maps.tsx` (real map).
- Session: stored in `localStorage` (`src/auth/session.web.ts`) instead of SecureStore.
- Push: not available in the browser. Email alerts and the in-app History still work.
- The backend allows the Expo web origin through CORS (`CORS_ORIGINS`, default
  `http://localhost:8081,http://127.0.0.1:8081`).

## Run on the iPhone (Expo Go, after the AWS deploy)

```
cd mobile
npx expo start         # or: npx expo start --clear
```

1. Install Expo Go from the App Store (it must support SDK 58).
2. Set `EXPO_PUBLIC_API_URL` to the public AWS backend URL in `mobile/.env.local`.
3. Scan the QR code shown in the terminal with the iPhone Camera app and tap the banner to
   open it in Expo Go.
4. If the LAN does not work (guest Wi-Fi, VPN), use `npx expo start --tunnel`.

## Configuration

Create `mobile/.env.local` (gitignored) from `mobile/.env.example`:

| Variable | Meaning |
|---|---|
| `EXPO_PUBLIC_USE_MOCK` | `1` (default): offline mock data with a permanent "MOCK DATA" banner. `0`: real backend. |
| `EXPO_PUBLIC_API_URL` | Backend base URL: `http://localhost:8000` for web testing, the public AWS URL for Expo Go. Empty forces mock mode. |
| `EXPO_PUBLIC_EAS_PROJECT_ID` | Optional EAS project id for Expo push tokens (or run `npx eas-cli init` once, which writes it into app.json). |

`EXPO_PUBLIC_*` values are bundled into the app: never put secrets there. Restart
`npx expo start` after changing them.

Pointing at the backend:
- Web, local: `docker compose up` at the repo root (backend only), then
  `EXPO_PUBLIC_API_URL=http://localhost:8000` and `EXPO_PUBLIC_USE_MOCK=0`.
- Expo Go: `EXPO_PUBLIC_API_URL=https://<public AWS backend URL>`.

## Mock mode

Mock mode (`src/api/mock.ts`, `src/api/mockData.ts`) keeps users, AOIs and read flags in
memory, so the whole flow works offline: any email, any 6-digit code. Every number in mock
mode is arbitrary and flagged as mock.

## Notifications

- iPhone in Expo Go: push works once the app has an EAS project id (see above) and the user
  grants permission. Taps on a push with `data.alert_id` open the alert detail.
- Android in Expo Go: remote push is not available since SDK 53. The app skips push there
  and does not load `expo-notifications`, so it does not crash.

## Layout

```
src/app/            routes (Expo Router): login, verify, onboarding, (tabs)/{index,zones,history,profile},
                    zones/draw, zones/[id], alerts/[id], change-email
src/api/            client.ts (entry), http.ts, mock.ts, mockData.ts, types.ts
src/auth/           session (SecureStore; session.web.ts uses localStorage), AuthProvider, providers.ts (Google/Apple extension point)
src/i18n/           es.ts (default, source of keys), en.ts
src/geo/            point in polygon, centroid, circles
src/notifications/  guarded push helpers
src/ui/             theme, shared components, maps.tsx (native) and maps.web.tsx (schematic web map)
```

Checks: `npx tsc --noEmit`, `npx expo-doctor`.
