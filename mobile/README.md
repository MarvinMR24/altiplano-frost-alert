# mobile (module 3)

Expo (SDK 58), React Native, TypeScript and Expo Router, for Expo Go on an iPhone. No
development build and no custom native modules. Talks to the backend only through the HTTP
API in `docs/api_contract.md`.

## Run (supported way: on the host)

```
cd mobile
npm install            # .npmrc sets legacy-peer-deps (web-only react-dom peer conflict)
npx expo start         # or: npx expo start --clear
```

1. Install Expo Go from the App Store (it must support SDK 58).
2. Put the iPhone on the same Wi-Fi as the Mac.
3. Scan the QR code shown in the terminal with the iPhone Camera app and tap the banner to
   open it in Expo Go.
4. If the LAN does not work (guest Wi-Fi, VPN), use `npx expo start --tunnel`.

## Configuration

Create `mobile/.env.local` (gitignored) from `mobile/.env.example`:

| Variable | Meaning |
|---|---|
| `EXPO_PUBLIC_USE_MOCK` | `1` (default): offline mock data with a permanent "MOCK DATA" banner. `0`: real backend. |
| `EXPO_PUBLIC_API_URL` | Backend base URL: the public ngrok URL `https://<name>.ngrok-free.app` or `http://<LAN-IP>:8000`. Empty forces mock mode. |
| `EXPO_PUBLIC_EAS_PROJECT_ID` | Optional EAS project id for Expo push tokens (or run `npx eas-cli init` once, which writes it into app.json). |

`EXPO_PUBLIC_*` values are bundled into the app: never put secrets there. Restart
`npx expo start` after changing them.

Pointing at the backend:
- ngrok (works from any network): `docker compose up` at the repo root, then
  `EXPO_PUBLIC_API_URL=https://<NGROK_DOMAIN>`. Every request sends
  `ngrok-skip-browser-warning: 1`.
- LAN: `EXPO_PUBLIC_API_URL=http://<your Mac LAN IP>:8000` (`ipconfig getifaddr en0`). Plain
  http to a LAN IP works in Expo Go during development.

## Mock mode

Mock mode (`src/api/mock.ts`, `src/api/mockData.ts`) keeps users, AOIs and read flags in
memory, so the whole flow works offline: any email, any 6-digit code. Every number in mock
mode is arbitrary and flagged as mock.

## Notifications

- iPhone in Expo Go: push works once the app has an EAS project id (see above) and the user
  grants permission. Taps on a push with `data.alert_id` open the alert detail.
- Android in Expo Go: remote push is not available since SDK 53. The app skips push there
  and does not load `expo-notifications`, so it does not crash.

## Docker (best effort)

`docker compose --profile mobile up mobile` runs `npx expo start --lan` in a `node:22-slim`
container with `REACT_NATIVE_PACKAGER_HOSTNAME=${HOST_LAN_IP}`. It needs `HOST_LAN_IP` in
`.env`. Tested on macOS: Metro starts and serves the manifest and bundle at
`exp://<HOST_LAN_IP>:8081`. The QR code is printed in the logs
(`docker compose --profile mobile logs -f mobile`). File watching through the bind mount can
be slow on macOS. Prefer the host setup above.

## Layout

```
src/app/            routes (Expo Router): login, verify, onboarding, (tabs)/{index,zones,history,profile},
                    zones/draw, zones/[id], alerts/[id], change-email
src/api/            client.ts (entry), http.ts, mock.ts, mockData.ts, types.ts
src/auth/           session (SecureStore), AuthProvider, providers.ts (Google/Apple extension point)
src/i18n/           es.ts (default, source of keys), en.ts
src/geo/            point in polygon, centroid, circles
src/notifications/  guarded push helpers
src/ui/             theme and shared components
```

Checks: `npx tsc --noEmit`, `npx expo-doctor`.
