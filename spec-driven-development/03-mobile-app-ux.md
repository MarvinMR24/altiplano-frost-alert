# Spec 03: Mobile app and UX

Status: approved
Module: `mobile/` (Expo SDK 58, Expo Router, TypeScript; runs on the host, not in Docker)
Depends on: `docs/api_contract.md`, spec 01, spec 02

## Why

The app is what the judges and the users see. It must show tonight's frost risk for the
user's areas in a few seconds, say clearly what to do, and stay honest about the data
(reanalysis, processed nights, not live).

## What

The screens already exist in mock mode. This spec covers the v2 auth flow, the four
languages, the catalog pickers, the threshold explanation, the calendar night picker, the
custom icon set and the logo.

1. Coverage from the backend: the 8 points of `configs/points.yaml` (El Alto, Oruro,
   Patacamaya, Calamarca, Caracollo, Corocoro, Charana, Huanuni) come from `GET /coverage`
   and `GET /map`. In real mode nothing about points is hardcoded. Mock data uses the same 8
   point ids and names, and every mock number stays flagged as mock.
2. Remove any reference to places outside the coverage (for example Puno, Juliaca, Cusco,
   Potosi, La Paz presets) from screens and copy.
3. Map: the 8 cells with their level for the selected night, a calendar night selector
   from `GET /nights`, tap a cell to see probability, level and conditions.
4. Zones: draw a polygon inside the coverage, pick a threshold of 30, 50 or 70 percent,
   choose channels (push, email). Show the cell used and its distance.
5. Alert detail, in this order:
   1. level (color, text and icon) and probability in percent;
   2. Muse explanation: headline, why, what to do (by profile);
   3. caveats;
   4. "How this was computed" (collapsed): model version, validation metrics summary,
      historical reliability for that probability range, data source.
6. Explanation label: "Explained with AI (Muse Spark)" when `source` is `muse`, "Automatic
   summary" when `source` is `template`.
7. Replay alerts show a visible "Replay" tag in History and in the detail.
8. Auth: a welcome screen (logo, tagline, language chips, create account, sign in, Google
   button), a 4-step sign up (about you, account with password rules and a strength meter,
   email code, profile), sign in with password or with a code, and forgot password with
   email, code and new password steps. Sign in with Google works when the backend has the
   Google settings and shows "coming soon" otherwise. There is no Apple sign in.
9. Languages: Spanish, English, Aymara ("Aymar aru") and Quechua ("Runa simi"). Aymara and
   Quechua are partial; missing keys fall back to Spanish (see `docs/i18n_review.md`) and
   the app shows a "partial translation" note. Alert emails and explanations exist only in
   es and en; ay and qu users get the Spanish version.
10. Crops (40+ items, 6 categories) and livestock (14 items) are picked with one reusable
    searchable `CatalogPicker` (accent-insensitive search over the current language, Spanish
    and synonyms; removable chips; grouped results; full-screen modal on phones). Old tag
    ids are kept so existing users keep working.
11. The default threshold is explained in the app as "Alert me from" with three plain-word
    options and an info sheet showing the 0 to 100 bar with the level colors at the 30, 50
    and 70 cut points. The same component is used in sign up, Profile, zone creation and
    zone editing.
12. The Map night selector is a compact pill (calendar icon, short localized date, pencil)
    under the search bar, next to a small "Reanalysis" chip that explains "Reanalysis data,
    processed nights. Not live and not a forecast." Tapping the pill opens a calendar bottom
    sheet (Monday-first grid, month and year jump, only available nights enabled, latest night
    marked, "Latest night" and "Cancel" buttons). The grid logic lives in the pure helper
    `src/date/calendar.ts` with unit tests.
13. All icons come from the custom `src/ui/icons/` set (react-native-svg, outline style,
    `<Icon name="..." />`); Ionicons stays only for the Google brand glyph.
14. The logo is the detailed Altiplano night mark (`assets/logo.svg`, `logo-horizontal.svg`,
    `logo-mono.svg`, rendered by `src/ui/logo.tsx`); PNGs are regenerated with
    `node scripts/build-icons.mjs`.

## Test environments

The app is not containerized. It is tested in two stages:
1. Local web (now): `npx expo start --web` against the backend on `http://localhost:8000`.
   The web build is for testing only. Maps use a real Leaflet base map
   (`src/ui/maps.web.tsx`, CARTO Voyager over OpenStreetMap), the session uses
   `localStorage`, and push is not available.
2. Expo Go on the iPhone on the same Wi-Fi (no cloud): against
   `http://<Mac IP>:8000` with `docker compose up` on the Mac. Push is verified here.

## UX rules

- Level is never shown by color alone: always color, text and icon.
- Every screen with risk shows the night date and "Reanalysis data". On the Map tab the night
  pill and the "Reanalysis" chip satisfy this; the full warning stays in the calendar sheet.
  Never "live", "now" or "real time".
- Maps (Map tab, zone drawing, zone detail) default to satellite imagery with place names
  (Apple or Google hybrid on the phone, Esri World Imagery on the web) and a round layers
  button switches to the street map; the choice is remembered per device. Shapes have a
  light halo so they read on imagery.
- A search bar on the Map tab and the draw screen finds towns, communities and places:
  the 8 coverage cells first (offline), then Photon with Nominatim as fallback (no key,
  debounced, at most one request per second, cached). Places outside the coverage are
  dimmed; they move the camera on the Map tab (with a "no frost data" note) and cannot be
  chosen on the draw screen. "My location" asks for foreground permission only when
  tapped, after a short explanation, and the position is never stored or sent.
- Spanish by default; the language selector (Español, English, Aymar aru, Runa simi)
  switches without restarting. Every key exists in `es.ts`, `en.ts`, `ay.ts` and `qu.ts`
  (`node scripts/check-i18n.mjs`); ay/qu fall back to Spanish per key.
- Short sentences, no jargon on the main screens, technical detail only inside "How this was
  computed". No em dashes.
- Every screen has loading, empty and error states with a retry action.
- Touch targets of at least 44 pt, text contrast at least 4.5:1, respects the system font
  size.
- No health or medical advice anywhere.
- Mock mode keeps the permanent "MOCK DATA" banner.

## Acceptance criteria

1. With `EXPO_PUBLIC_USE_MOCK=0` and the backend running, the Map shows exactly the 8 points
   returned by `/coverage`, with no point defined in app code (code search plus manual check).
2. No screen or i18n string mentions a place outside the coverage (search test over
   `src/`).
3. Every number on screen comes from the API or mock data flagged as mock; no literal metric
   or probability in components (code review checklist in `docs/status.md`).
4. Tapping a push with `data.alert_id` opens the matching alert detail (manual check on the
   iPhone).
5. The alert detail shows the sections in the order above and the correct explanation label
   for `muse` and `template` (manual check with one of each).
6. The language selector switches every visible string; the key check script finds every
   key in all four dictionaries, with ay/qu falling back to Spanish per key.
7. Loading, empty and error states exist for Map, Zones, History and alert detail (manual
   check with the backend stopped).
8. "Delete my data" in Profile calls `DELETE /me`, clears the session and returns to the
   welcome screen.
9. `npx tsc --noEmit`, `npx expo-doctor` and `npx expo export --platform web` pass, plus
   `node scripts/check-i18n.mjs` and `node scripts/unit-tests.mjs`.
10. Local web: welcome, create account through the four steps, sign out, sign in with
    password, sign in with code, forgot password, crop and livestock search, threshold info
    sheet, calendar jump to 2024-08-17 and back to the latest night, with the backend
    running on `localhost:8000` and in mock mode.
11. On the builder's iPhone in Expo Go on the same Wi-Fi: welcome, create account,
    onboarding, create an AOI, receive the replay alert by push, open it, read the
    explanation.
12. Alert detail shows a "Replay" tag when the payload carries `mode: "replay"` and an
    explanation label from the optional `explanation_source` (`muse` or `template`).
    Mock data provides both sources for manual checks. Note: the backend detail
    endpoint already sends `mode`, but the alerts list does not, so the History tag
    only appears when the summary carries it; `explanation_source` is not exposed by
    the backend yet, so real alerts fall back to the template label until it is.
