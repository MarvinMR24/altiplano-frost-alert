# i18n review: Aymara and Quechua

Status: partial translations, under review by native speakers. The app shows a
note under the language selector when Aymara or Quechua is chosen.

How the fallback works: `mobile/src/i18n/ay.ts` and `mobile/src/i18n/qu.ts`
spread the Spanish dictionary and override only the keys listed as translated.
Every key below currently shows the Spanish text. Nothing was machine-invented:
keys are translated only where the words are well established, and every
translated string still needs a native speaker to confirm it.

Run `node scripts/check-i18n.mjs` in `mobile/` to verify key parity
(es is the source of truth, en matches it exactly, ay/qu override a subset).

Shared words kept identical to Spanish on purpose (borrowed terms used in the
community): Cuenta, Perfil, Papa, Llama, Mapa, Carpa solar, Contraseña,
Alfalfa, Siwara.

Calendar month and weekday names fall back to Spanish for ay/qu (standard
practice in Bolivia; listed with the calendar keys below).

Crop and livestock catalogs (`mobile/src/catalog/`): ay/qu labels exist only
for well-known names (quinua, ch'uñu, tunta, apilla/uqa, ulluku, isañu,
kañiwa, jawas/hawas, qarwa, allpaqa, iwija/uwiha, waka, khuchi, wallpa,
wank'u/quwi, kawallu, asnu). Every other item falls back to Spanish at
runtime through `labelFor`.

## Aymara (ay): keys showing Spanish

### common (10)

- `common.networkError`
- `common.saved`
- `common.close`
- `common.mockBanner`
- `common.reanalysis`
- `common.reanalysisNote`
- `common.percent`
- `common.or`
- `common.showPassword`
- `common.hidePassword`

### auth (13)

- `auth.title`
- `auth.subtitle`
- `auth.emailPlaceholder`
- `auth.invalidEmail`
- `auth.codeTitle`
- `auth.codeSubtitle`
- `auth.codeLabel`
- `auth.invalidCode`
- `auth.codeFormat`
- `auth.codeResent`
- `auth.mockHint`
- `auth.passwordLabel`
- `auth.mockPasswordHint`

### onboarding (13)

- `onboarding.step`
- `onboarding.languageTitle`
- `onboarding.producerDesc`
- `onboarding.residentDesc`
- `onboarding.cropsTitle`
- `onboarding.notificationsTitle`
- `onboarding.notificationsBody`
- `onboarding.enableNotifications`
- `onboarding.notificationsEnabled`
- `onboarding.notificationsDenied`
- `onboarding.notificationsUnavailable`
- `onboarding.emailNote`
- `onboarding.finish`

### map (15)

- `map.previous`
- `map.next`
- `map.latest`
- `map.legend`
- `map.coverage`
- `map.yourZones`
- `map.level`
- `map.drivers`
- `map.conditions`
- `map.reliability`
- `map.reliabilityText`
- `map.elevation`
- `map.modelVersion`
- `map.webPreview`
- `map.noData`

### driver (2)

- `driver.up`
- `driver.down`

### feature (10)

- `feature.t2m_c`
- `feature.d2m_c`
- `feature.rh_pct`
- `feature.wind_ms`
- `feature.tcc_pct`
- `feature.sp_hpa`
- `feature.lw_down_wm2`
- `feature.dewpoint_depression_c`
- `feature.t2m_drop_1200_1800_c`
- `feature.doy`

### zones (10)

- `zones.empty`
- `zones.threshold`
- `zones.channels`
- `zones.push`
- `zones.email`
- `zones.none`
- `zones.deleteTitle`
- `zones.deleteBody`
- `zones.noCurrent`
- `zones.cellUsed`

### draw (21)

- `draw.title`
- `draw.hint`
- `draw.hintIos`
- `draw.midHint`
- `draw.deleteVertex`
- `draw.invalidOutside`
- `draw.vertices`
- `draw.undo`
- `draw.clear`
- `draw.finish`
- `draw.maxReached`
- `draw.outside`
- `draw.outsideBody`
- `draw.formTitle`
- `draw.nameLabel`
- `draw.namePlaceholder`
- `draw.nameRequired`
- `draw.thresholdLabel`
- `draw.channelsLabel`
- `draw.saveZone`
- `draw.editTitle`

### history (13)

- `history.title`
- `history.empty`
- `history.explainedMuse`
- `history.explainedTemplate`
- `history.unread`
- `history.outcome`
- `history.outcomeUnknown`
- `history.sentVia`
- `history.trainedYears`
- `history.cells`
- `history.validation`
- `history.test`
- `history.limitations`

### metric (9)

- `metric.pr_auc`
- `metric.f2`
- `metric.precision`
- `metric.recall`
- `metric.f1`
- `metric.roc_auc`
- `metric.brier`
- `metric.accuracy`
- `metric.majority_accuracy`

### profile (9)

- `profile.title`
- `profile.changeEmailTitle`
- `profile.newEmail`
- `profile.emailChanged`
- `profile.defaultThreshold`
- `profile.deleteBody`
- `profile.changePassword`
- `profile.changePasswordTitle`
- `profile.dangerZone`

### language (4)

- `language.es`
- `language.en`
- `language.ay`
- `language.qu`

### welcome (3)

- `welcome.google`
- `welcome.apple`
- `welcome.comingSoon`

### signup (10)

- `signup.namePlaceholder`
- `signup.nameLength`
- `signup.phoneLabel`
- `signup.phonePlaceholder`
- `signup.phoneInvalid`
- `signup.passwordMismatch`
- `signup.ruleLength`
- `signup.ruleLetter`
- `signup.ruleNumber`
- `signup.successBody`

### signin (2)

- `signin.notVerified`
- `signin.rateLimited`

### forgot (5)

- `forgot.title`
- `forgot.emailBody`
- `forgot.codeBody`
- `forgot.newPasswordBody`
- `forgot.success`

### password (5)

- `password.current`
- `password.new`
- `password.confirm`
- `password.changed`
- `password.wrongCurrent`

### picker (1)

- `picker.maxReached`

### category (2)

- `category.legume`
- `category.forage`

### threshold (8)

- `threshold.title`
- `threshold.30`
- `threshold.50`
- `threshold.70`
- `threshold.infoLabel`
- `threshold.sheetTitle`
- `threshold.sheetBody`
- `threshold.chosen`

### calendar (4)

- `calendar.selectYear`
- `calendar.selectMonth`
- `calendar.processedWarning`
- `calendar.noNights`
## Quechua (qu): keys showing Spanish

### common (8)

- `common.networkError`
- `common.saved`
- `common.mockBanner`
- `common.reanalysis`
- `common.reanalysisNote`
- `common.percent`
- `common.showPassword`
- `common.hidePassword`

### auth (13)

- `auth.title`
- `auth.subtitle`
- `auth.emailPlaceholder`
- `auth.invalidEmail`
- `auth.codeTitle`
- `auth.codeSubtitle`
- `auth.codeLabel`
- `auth.invalidCode`
- `auth.codeFormat`
- `auth.codeResent`
- `auth.mockHint`
- `auth.passwordLabel`
- `auth.mockPasswordHint`

### onboarding (13)

- `onboarding.step`
- `onboarding.languageTitle`
- `onboarding.producerDesc`
- `onboarding.residentDesc`
- `onboarding.cropsTitle`
- `onboarding.notificationsTitle`
- `onboarding.notificationsBody`
- `onboarding.enableNotifications`
- `onboarding.notificationsEnabled`
- `onboarding.notificationsDenied`
- `onboarding.notificationsUnavailable`
- `onboarding.emailNote`
- `onboarding.finish`

### map (15)

- `map.previous`
- `map.next`
- `map.latest`
- `map.legend`
- `map.coverage`
- `map.yourZones`
- `map.level`
- `map.drivers`
- `map.conditions`
- `map.reliability`
- `map.reliabilityText`
- `map.elevation`
- `map.modelVersion`
- `map.webPreview`
- `map.noData`

### driver (2)

- `driver.up`
- `driver.down`

### feature (10)

- `feature.t2m_c`
- `feature.d2m_c`
- `feature.rh_pct`
- `feature.wind_ms`
- `feature.tcc_pct`
- `feature.sp_hpa`
- `feature.lw_down_wm2`
- `feature.dewpoint_depression_c`
- `feature.t2m_drop_1200_1800_c`
- `feature.doy`

### zones (10)

- `zones.empty`
- `zones.threshold`
- `zones.channels`
- `zones.push`
- `zones.email`
- `zones.none`
- `zones.deleteTitle`
- `zones.deleteBody`
- `zones.noCurrent`
- `zones.cellUsed`

### draw (21)

- `draw.title`
- `draw.hint`
- `draw.hintIos`
- `draw.midHint`
- `draw.deleteVertex`
- `draw.invalidOutside`
- `draw.vertices`
- `draw.undo`
- `draw.clear`
- `draw.finish`
- `draw.maxReached`
- `draw.outside`
- `draw.outsideBody`
- `draw.formTitle`
- `draw.nameLabel`
- `draw.namePlaceholder`
- `draw.nameRequired`
- `draw.thresholdLabel`
- `draw.channelsLabel`
- `draw.saveZone`
- `draw.editTitle`

### history (13)

- `history.title`
- `history.empty`
- `history.explainedMuse`
- `history.explainedTemplate`
- `history.unread`
- `history.outcome`
- `history.outcomeUnknown`
- `history.sentVia`
- `history.trainedYears`
- `history.cells`
- `history.validation`
- `history.test`
- `history.limitations`

### metric (9)

- `metric.pr_auc`
- `metric.f2`
- `metric.precision`
- `metric.recall`
- `metric.f1`
- `metric.roc_auc`
- `metric.brier`
- `metric.accuracy`
- `metric.majority_accuracy`

### profile (9)

- `profile.title`
- `profile.changeEmailTitle`
- `profile.newEmail`
- `profile.emailChanged`
- `profile.defaultThreshold`
- `profile.deleteBody`
- `profile.changePassword`
- `profile.changePasswordTitle`
- `profile.dangerZone`

### language (4)

- `language.es`
- `language.en`
- `language.ay`
- `language.qu`

### welcome (3)

- `welcome.google`
- `welcome.apple`
- `welcome.comingSoon`

### signup (10)

- `signup.namePlaceholder`
- `signup.nameLength`
- `signup.phoneLabel`
- `signup.phonePlaceholder`
- `signup.phoneInvalid`
- `signup.passwordMismatch`
- `signup.ruleLength`
- `signup.ruleLetter`
- `signup.ruleNumber`
- `signup.successBody`

### signin (2)

- `signin.notVerified`
- `signin.rateLimited`

### forgot (5)

- `forgot.title`
- `forgot.emailBody`
- `forgot.codeBody`
- `forgot.newPasswordBody`
- `forgot.success`

### password (5)

- `password.current`
- `password.new`
- `password.confirm`
- `password.changed`
- `password.wrongCurrent`

### picker (1)

- `picker.maxReached`

### threshold (8)

- `threshold.title`
- `threshold.30`
- `threshold.50`
- `threshold.70`
- `threshold.infoLabel`
- `threshold.sheetTitle`
- `threshold.sheetBody`
- `threshold.chosen`

### calendar (4)

- `calendar.selectYear`
- `calendar.selectMonth`
- `calendar.processedWarning`
- `calendar.noNights`
