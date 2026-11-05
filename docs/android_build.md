# Android APK with EAS Build and Google Maps

The Android app is built in the cloud with EAS Build as an installable APK (profile
`preview`) and published as a GitHub Release asset. iPhone users keep Expo Go (iOS
standalone builds are out of scope). Config: `mobile/app.config.ts` (package
`com.marvinmr24.frostwatch`) and `mobile/eas.json`.

Maps: Android uses Google Maps through react-native-maps (`PROVIDER_GOOGLE` in
`mobile/src/ui/maps.tsx`), with satellite (hybrid) and street layers. iOS keeps Apple Maps
and the web keeps Leaflet with Esri. We use only the **Maps SDK for Android**: no Google
web maps, Geocoding or Places (place search stays on Photon and Nominatim).

Before you start, the backend must be online over HTTPS (`docs/deploy_aws.md`): release
builds block plain http, and the APK talks only to `https://<DOMAIN>`.

## 1. Expo account and EAS project

```bash
cd mobile
npx eas-cli login                 # create the account at https://expo.dev/signup first
npx eas-cli init                  # creates the EAS project and prints its id
```

Because the config is dynamic (`app.config.ts`), `eas init` cannot write the id for you:
paste the printed id into `EAS_PROJECT_ID_FROM_INIT` in `mobile/app.config.ts` (it is not a
secret). Then set the backend URL in `mobile/eas.json`: replace
`https://REPLACE_WITH_YOUR_DOMAIN` in the `preview` and `production` profiles with
`https://<DOMAIN>`.

## 2. Google Maps key (Google Cloud)

1. https://console.cloud.google.com > create a project `frostwatch`.
2. Billing > link a billing account (Google requires it even for free APIs).
3. APIs & Services > Library > enable **Maps SDK for Android** only.
4. APIs & Services > Credentials > Create credentials > API key.
5. Restrict the key (mandatory: a Maps key always ends up inside the APK, anyone can read
   it from the file):
   - Application restrictions: **Android apps** > Add: package name
     `com.marvinmr24.frostwatch` and the **SHA-1 certificate fingerprint** of the EAS
     keystore. Get it with:
     ```bash
     npx eas-cli credentials -p android
     ```
     choose the `preview` profile, then Keystore; if there is none yet, let EAS generate
     one, and copy the SHA1 fingerprint it shows. (The `production` profile uses the same
     keystore unless you change it.)
   - API restrictions: **Restrict key** > only **Maps SDK for Android**.
6. Billing > Budgets & alerts > create a budget of **1 USD** with email alerts.

Cost: the Maps SDK for Android has no charge for map loads in mobile apps (check the current
Google Maps Platform pricing page). We call no paid Google API.

## 3. Store the key as an EAS secret

Never put the key in the repo, `eas.json` or `.env` files. Store it in EAS (secret
visibility: build servers can read it, nobody can read it back):

```bash
read -rs MAPS_KEY                 # paste the key, Enter (keeps it out of shell history)
npx eas-cli env:set --name GOOGLE_MAPS_API_KEY --value "$MAPS_KEY" \
  --environment preview --environment production --visibility secret --scope project
unset MAPS_KEY
```

(`eas env:create` still exists in eas-cli 27 but is deprecated in favor of `env:set`.)
`app.config.ts` reads it into `android.config.googleMaps.apiKey`; without it the build
works but the map is empty, and the config prints a warning.

## 4. Build the APK

```bash
cd mobile
npx eas-cli build -p android --profile preview
```

Each APK you publish needs a higher `versionCode`: `ANDROID_VERSION_CODE=2 npx eas-cli
build ...` (or bump the default in `app.config.ts`), and bump `VERSION` for a new release.
When the build finishes, download the `.apk` from the link EAS prints (or expo.dev > your
project > Builds). Never commit it (`*.apk` and `*.aab` are gitignored).

## 5. Test on a real Android phone

Install the APK (allow installs from your browser or file manager when Android asks), then:

1. Sign up or sign in (email code or password; Google if configured on the backend).
2. Map tab: satellite imagery loads, the layers button switches to the street map, the 8
   cells show their names and levels, tapping a cell opens the Muse explanation.
3. Zones: draw a zone at close zoom over the imagery, move and delete a point, save it.
4. History: replay an alert from the server (`docs/deploy_aws.md` step 6) and open it.

If the map is grey with a Google logo, the key is missing or its restrictions do not match
the package name and SHA-1.

If the app closes right after opening, read the crash with `adb logcat -b crash`. SDK 58
minifies release builds with R8; `app.config.ts` keeps Room's generated classes through
`expo-build-properties` (`extraProguardRules`), because without them WorkManager (pulled in
by react-native-maps) crashes at start with "Failed to create an instance of class
androidx.work.impl.WorkDatabase".

## 6. Publish

On GitHub: Releases > Draft a new release > tag `v1.0.0` > attach the APK file
(for example `frostwatch-1.0.0.apk`) > Publish. The README "Download" section points there.

## 7. Push notifications on Android (optional)

Expo Go handled push for us; a standalone Android app needs Firebase Cloud Messaging (FCM)
V1 credentials. Without them the app works normally: alerts still arrive by email and are
listed in History.

1. https://console.firebase.google.com > Add project (it can reuse the Google Cloud project).
2. Add an Android app with package `com.marvinmr24.frostwatch` and download
   `google-services.json`. Do not commit it: upload it as an EAS file variable
   (`npx eas-cli env:set --name GOOGLE_SERVICES_JSON --type file --value ./google-services.json --environment preview --visibility secret`)
   and reference it from `app.config.ts` as `android.googleServicesFile:
   process.env.GOOGLE_SERVICES_JSON` (not done yet).
3. Firebase console > Project settings > Service accounts > Generate new private key (a JSON
   file, keep it off the repo).
4. `npx eas-cli credentials -p android` > Google Service Account > Manage your Google
   Service Account Key for Push Notifications (FCM V1) > upload that JSON.
5. Rebuild the APK.

Guide: https://docs.expo.dev/push-notifications/fcm-credentials/
