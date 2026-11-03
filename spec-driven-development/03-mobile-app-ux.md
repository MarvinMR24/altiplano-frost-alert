# Spec 03: Mobile app and UX

Status: approved
Module: `mobile/` (Expo SDK 58, Expo Router, TypeScript, Expo Go on iPhone)
Depends on: `docs/api_contract.md`, spec 01, spec 02

## Why

The app is what the judges and the users see. It must show tonight's frost risk for the
user's areas in a few seconds, say clearly what to do, and stay honest about the data
(reanalysis, processed nights, not live).

## What

The screens already exist in mock mode (login, verify, onboarding, Map, Zones with polygon
drawing, History, alert detail, Profile, change email). This spec covers the move to real data
and the UX rules.

1. Coverage from the backend: the 8 points of `configs/points.yaml` (El Alto, Oruro,
   Patacamaya, Calamarca, Caracollo, Corocoro, Charana, Huanuni) come from `GET /coverage`
   and `GET /map`. In real mode nothing about points is hardcoded. Mock data uses the same 8
   point ids and names, and every mock number stays flagged as mock.
2. Remove any reference to places outside the coverage (for example Puno, Juliaca, Cusco,
   Potosi, La Paz presets) from screens and copy.
3. Map: the 8 cells with their level for the selected night, a night selector from
   `GET /nights`, tap a cell to see probability, level and conditions.
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

## UX rules

- Level is never shown by color alone: always color, text and icon.
- Every screen with risk shows "Night of dd/mm" and "Reanalysis data". Never "live", "now" or
  "real time".
- Spanish by default, English toggle that switches without restarting. Every key exists in
  `es.ts` and `en.ts`.
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
6. Language toggle switches every visible string; a key check script finds no key missing in
   either dictionary.
7. Loading, empty and error states exist for Map, Zones, History and alert detail (manual
   check with the backend stopped).
8. "Delete my data" in Profile calls `DELETE /me`, clears the session and returns to login.
9. `npx tsc --noEmit` and `npx expo-doctor` pass.
10. The full demo flow works on the builder's iPhone in Expo Go: login, onboarding, create an
    AOI, receive the replay alert by push, open it, read the explanation.
