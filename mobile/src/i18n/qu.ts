// Quechua dictionary ("Runa simi", Southern Quechua as spoken in Bolivia).
// Keys not listed here fall back to Spanish at build time; every fallback key is listed
// in docs/i18n_review.md for a native speaker. Trivocalic a, i, u orthography.
// Every string below still needs native review.
import { es, type TranslationKey } from './es';

const quOverrides: Partial<Record<TranslationKey, string>> = {
  'common.loading': 'Suyay...',
  'common.error': 'Pantay.',
  'common.retry': 'Huktawan',
  'common.save': 'Waqaychay',
  'common.cancel': 'Manam',
  'common.delete': 'Pichay',
  'common.edit': 'Hukchay',
  'common.close': "Wisq'ay",
  'common.next': 'Qhipa',
  'common.back': 'Kutiy',
  'common.done': 'Allin',
  'common.or': 'icha',
  'common.night': 'Tuta {date}',

  'level.low': 'Pisi',
  'level.moderate': 'Chawpi',
  'level.high': 'Hatun',
  'level.very_high': 'Ancha hatun',

  'auth.emailLabel': 'Correo',
  'auth.sendCode': 'Codigota apachiy',
  'auth.verify': 'Cheqanchay',
  'auth.resend': 'Huktawan apachiy',
  'auth.changeEmail': 'Huk correowan',
  'auth.resendIn': 'Huktawan apachiy: {s}',

  'welcome.tagline': 'Qasa willaykuna.',
  'welcome.createAccount': 'Musuq cuenta kichay',
  'welcome.signIn': 'Yaykuy',

  'signup.aboutYou': 'Qanmanta',
  'signup.account': 'Cuenta',
  'signup.verifyEmail': 'Correota cheqanchay',
  'signup.profile': 'Perfil',
  'signup.nameLabel': "Hunt'a suti",
  'signup.passwordLabel': 'Contraseña',
  'signup.confirmPassword': 'Contraseñata huktawan',
  'signup.strengthWeak': 'Pisi kallpayuq',
  'signup.strengthFair': 'Chawpi',
  'signup.strengthStrong': 'Kallpayuq',
  'signup.successTitle': 'Cuental allin',
  'signup.goToMap': 'Mapaman riy',

  'signin.title': 'Yaykuy',
  'signin.forgotPassword': '¿Contraseñaykita qonqarqankichu?',
  'signin.withCode': 'Codigowan yaykuy',
  'signin.wrongCredentials': 'Correo icha contraseñapis pantasqam.',

  'onboarding.profileTitle': '¿Imaynataq apaykachanki?',
  'onboarding.producer': 'Tarpuq',
  'onboarding.resident': 'Tiyaq',
  'onboarding.cropsLabel': 'Tarpuykuna',
  'onboarding.livestockLabel': 'Uywakuna',

  'crop.potato': 'Papa',
  'crop.quinoa': 'Kinwa',
  'crop.barley': 'Siwara',
  'crop.broad_bean': 'Hawas',
  'crop.oca': 'Uqa',
  'crop.alfalfa': 'Alfalfa',
  'livestock.llama': 'Llama',
  'livestock.alpaca': 'Alpaka',
  'livestock.sheep': 'Uwiha',
  'livestock.cattle': 'Waka',

  'tabs.map': 'Mapa',
  'tabs.zones': 'Suyukuna',
  'tabs.history': 'Ñawpa',
  'tabs.profile': 'Perfil',

  'map.probability': 'Qasa hamunman',
  'map.whatHappened': '¿Imataq pasarqan?',
  'map.frostObserved': 'Qasarqamun. Mínima {t} °C.',
  'map.noFrostObserved': 'Manam qasarqamunchu. Mínima {t} °C.',
  'map.notYetKnown': 'Manam yachakunchu.',

  'zones.title': 'Suyukuna',
  'zones.add': 'Musuq suyu',

  'history.replay': 'Huktawan',
  'history.why': '¿Imarayku?',
  'history.actions': '¿Imatataq ruwana?',
  'history.caveats': 'Yuyaychakuy',
  'history.howComputed': '¿Imayna yupana?',

  'picker.search': 'Maskhay',
  'picker.noResults': 'Manam kanchu.',
  'picker.remove': '{label}ta hurquy',

  'category.tuber': 'Papa',
  'category.grain': 'Grano',
  'category.legume': 'Purutu',
  'category.vegetable': 'Yuyu',
  'category.forage': 'Qachu',
  'category.greenhouse': 'Carpa solar',

  'calendar.editNight': 'Tutata hukchay',
  'calendar.latestNight': 'Qhipa tuta',

  'profile.name': 'Suti',
  'profile.email': 'Correo',
  'profile.notificationEmail': 'Willay correo',
  'profile.changeEmail': 'Hukchay',
  'profile.language': 'Simi',
  'profile.profileType': 'Perfil',
  'profile.alerts': 'Willaykuna',
  'profile.account': 'Cuenta',
  'profile.crops': 'Tarpuykuna',
  'profile.livestock': 'Uywakuna',
  'profile.editName': 'Sutita hukchay',
  'profile.deleteData': 'Datuykita pichay',
  'profile.deleteTitle': 'Datuykita pichay',
  'profile.signOut': 'Lluqsiy',

  'language.partialNote': 'Runa simipi: wakin simikunaraqmi qillqasqa, qhawanapaq.',
};

export const qu: Record<TranslationKey, string> = { ...es, ...quOverrides };
