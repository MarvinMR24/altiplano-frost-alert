// Aymara dictionary ("Aymar aru"). Keys not listed here fall back to Spanish at
// build time; every fallback key is listed in docs/i18n_review.md for a native speaker.
// Standard modern orthography. Every string below still needs native review.
import { es, type TranslationKey } from './es';

const ayOverrides: Partial<Record<TranslationKey, string>> = {
  'common.loading': 'Suyaña...',
  'common.error': 'Pantja.',
  'common.retry': 'Wasitata',
  'common.save': 'Imaña',
  'common.cancel': 'Janiwa',
  'common.delete': 'Pichjaña',
  'common.edit': 'Turkaña',
  'common.next': 'Qhipa',
  'common.back': "Kut'aña",
  'common.done': 'Wali',
  'common.night': 'Aruma {date}',

  'level.low': "Juk'a",
  'level.moderate': 'Taypi',
  'level.high': "Jach'a",
  'level.very_high': "Jach'a wali",

  'auth.emailLabel': 'Correo',
  'auth.sendCode': 'Código khithaña',
  'auth.verify': 'Cheqanchaña',
  'auth.resend': 'Wasitata khithaña',
  'auth.changeEmail': 'Yaqha correo',
  'auth.resendIn': 'Wasitata khithaña: {s}',

  'welcome.tagline': 'Juyphi iwxawinakawa.',
  'welcome.createAccount': 'Machaq cuenta luraña',
  'welcome.signIn': 'Mantaña',

  'signup.aboutYou': 'Jumata',
  'signup.account': 'Cuenta',
  'signup.verifyEmail': 'Correo cheqanchaña',
  'signup.profile': 'Perfil',
  'signup.nameLabel': 'Phuqha suti',
  'signup.passwordLabel': 'Contraseña',
  'signup.confirmPassword': 'Wasitata contraseña',
  'signup.strengthWeak': "Pisi ch'amani",
  'signup.strengthFair': 'Taypi',
  'signup.strengthStrong': "Ch'amani",
  'signup.successTitle': 'Cuentaxa waliwa',
  'signup.goToMap': 'Uñtawiru saraña',

  'signin.title': 'Mantaña',
  'signin.forgotPassword': '¿Contraseñama armasta?',
  'signin.withCode': 'Códigoampi mantaña',
  'signin.wrongCredentials': 'Correo jan ukaxa contraseña pantjatawa.',

  'onboarding.profileTitle': '¿Kunjamasa apnaqäta?',
  'onboarding.producer': 'Yapuchiri',
  'onboarding.resident': 'Jakiri',
  'onboarding.cropsLabel': 'Achunaka',
  'onboarding.livestockLabel': 'Uywanaka',

  'crop.potato': "Ch'uqi",
  'crop.quinoa': 'Juira',
  'crop.barley': 'Siwara',
  'crop.broad_bean': 'Jawasa',
  'crop.oca': 'Apilla',
  'crop.alfalfa': 'Alfalfa',
  'livestock.llama': 'Qarwa',
  'livestock.alpaca': 'Allpaqa',
  'livestock.sheep': 'Iwija',
  'livestock.cattle': 'Waka',

  'tabs.map': 'Uñtawi',
  'tabs.zones': 'Uraqikuna',
  'tabs.history': 'Nayra',
  'tabs.profile': 'Perfil',

  'map.probability': 'Juyphi utjaña',
  'map.whatHappened': '¿Kunasa tukuri?',
  'map.frostObserved': 'Juyphiw utji. Mínima {t} °C.',
  'map.noFrostObserved': 'Janiw juyphirikiti. Mínima {t} °C.',
  'map.notYetKnown': 'Janiw yatiskiti.',

  'zones.title': 'Uraqikuna',
  'zones.add': 'Machaq uraqi',

  'history.replay': 'Wasitata',
  'history.why': '¿Kunatsa?',
  'history.actions': '¿Kunasa luraña?',
  'history.caveats': 'Amuyaña',
  'history.howComputed': '¿Kunjamasa jakhuri?',

  'picker.search': 'Thaqaña',
  'picker.noResults': 'Janiw utjkiti.',
  'picker.remove': '{label} pichjaña',

  'category.tuber': "Ch'uqi",
  'category.grain': 'Juyra',
  'category.vegetable': "Ch'uxña achunaka",
  'category.greenhouse': 'Carpa solar',

  'calendar.editNight': 'Aruma turkaña',
  'calendar.latestNight': 'Qhipa aruma',

  'profile.name': 'Suti',
  'profile.email': 'Correo',
  'profile.notificationEmail': 'Iwxawi correo',
  'profile.changeEmail': 'Turkaña',
  'profile.language': 'Aru',
  'profile.profileType': 'Perfil',
  'profile.alerts': 'Iwxawinaka',
  'profile.account': 'Cuenta',
  'profile.crops': 'Achunaka',
  'profile.livestock': 'Uywanaka',
  'profile.editName': 'Suti turkaña',
  'profile.deleteData': 'Datunaka pichjaña',
  'profile.deleteTitle': 'Datunaka pichjaña',
  'profile.signOut': 'Mistuña',

  'language.partialNote': 'Aymar aru: juk’a arunakaw qillqata, uñakipañatakiwa.',
};

export const ay: Record<TranslationKey, string> = { ...es, ...ayOverrides };
