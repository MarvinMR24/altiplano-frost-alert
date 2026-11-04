// In-memory implementation of the API so the whole flow works offline (EXPO_PUBLIC_USE_MOCK=1).
// AOIs, read flags and users live in memory and reset when the app reloads.

import { centroid, fromPolygon, haversineKm, polygonInsideCoverage, toPolygon } from '@/geo';
import {
  MOCK_CELLS,
  MOCK_DATA_SOURCE,
  MOCK_EXPLANATION_TEXT,
  MOCK_MODEL_CARD,
  MOCK_MODEL_VERSION,
  MOCK_NIGHTS,
  mockCellsFor,
  mockCoverage,
} from './mockData';
import {
  ApiError,
  type AlertDetail,
  type AlertSummary,
  type Aoi,
  type AoiCreate,
  type AoiPatch,
  type Api,
  type AppleSignInInput,
  type AuthProviders,
  type CoverageResponse,
  type Language,
  type MapResponse,
  type ModelCard,
  type NightsResponse,
  type PlaceExplanation,
  type RegisterInput,
  type User,
  type UserPatch,
  type VerifyResponse,
} from './types';

function explanationText(language: string) {
  return MOCK_EXPLANATION_TEXT[language as 'es' | 'en'] ?? MOCK_EXPLANATION_TEXT.es;
}

const LATENCY_MS = 250;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CODE_RE = /^\d{6}$/;

function wait<T>(value: T, ms = LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

interface MockAlertRecord {
  id: string;
  aoi_id: string;
  aoi_name: string;
  night_date: string;
  point_id: string;
  channels_sent: ('push' | 'email')[];
  sent_at: string;
  read: boolean;
  mode: 'replay' | 'tick';
  explanation_source: 'muse' | 'template';
}

export class MockApi implements Api {
  private token: string | null = null;
  private users = new Map<string, User>();
  private passwords = new Map<string, string>();
  private coverage: CoverageResponse = mockCoverage();
  private aois: Aoi[] = [];
  private alerts: MockAlertRecord[] = [];
  private nextId = 1;

  constructor() {
    this.seed();
  }

  private seed() {
    // A sample zone around Patacamaya and a few alerts on past mock nights.
    const center = MOCK_CELLS.find((c) => c.point_id === 'patacamaya')!;
    const d = 0.05;
    const polygon = toPolygon([
      { latitude: center.lat + d, longitude: center.lon - d },
      { latitude: center.lat + d, longitude: center.lon + d },
      { latitude: center.lat - d, longitude: center.lon + d },
      { latitude: center.lat - d, longitude: center.lon - d },
    ]);
    const aoi: Aoi = {
      id: 'aoi-mock-1',
      name: 'Patacamaya (mock)',
      polygon,
      threshold: 50,
      channels: { push: true, email: true },
    };
    this.aois.push(aoi);
    const seeds: [string, string, boolean, 'replay' | 'tick', 'muse' | 'template'][] = [
      [MOCK_NIGHTS[0], 'patacamaya', true, 'replay', 'muse'],
      [MOCK_NIGHTS[1], 'calamarca', true, 'tick', 'template'],
      [MOCK_NIGHTS[3], 'patacamaya', false, 'replay', 'muse'],
    ];
    seeds.forEach(([night, pointId, read, mode, explanation_source], i) => {
      this.alerts.push({
        id: `alert-mock-${i + 1}`,
        aoi_id: aoi.id,
        aoi_name: aoi.name,
        night_date: night,
        point_id: pointId,
        channels_sent: ['push', 'email'],
        sent_at: `${night}T23:30:00Z`,
        read,
        mode,
        explanation_source,
      });
    });
  }

  setToken(token: string | null): void {
    this.token = token;
  }

  private currentUser(): User {
    if (!this.token?.startsWith('mock:')) throw new ApiError(401, 'unauthorized');
    const email = this.token.slice('mock:'.length);
    let user = this.users.get(email);
    if (!user) {
      // The app was reloaded: memory is gone but the stored session is still valid.
      user = this.newUser(email, true);
      this.users.set(email, user);
    }
    return user;
  }

  private newUser(email: string, onboarded: boolean): User {
    return {
      id: `user-${this.nextId++}`,
      email,
      name: null,
      phone: null,
      email_verified: true,
      language: 'es',
      profile: 'producer',
      crops: [],
      livestock: [],
      default_threshold: 50,
      notification_email: email,
      onboarded,
    };
  }

  async requestEmailCode(email: string): Promise<void> {
    if (!EMAIL_RE.test(email)) throw new ApiError(422, 'invalid_email');
    return wait(undefined);
  }

  async verifyEmailCode(email: string, code: string): Promise<VerifyResponse> {
    if (!CODE_RE.test(code)) throw new ApiError(400, 'invalid_code');
    let user = this.users.get(email);
    if (!user) {
      user = this.newUser(email, false);
      this.users.set(email, user);
    }
    user.email_verified = true;
    return wait({ session_token: `mock:${email}`, user: clone(user) });
  }

  async register(input: RegisterInput): Promise<void> {
    if (!EMAIL_RE.test(input.email)) throw new ApiError(422, 'invalid_email');
    const existing = this.users.get(input.email);
    if (existing?.email_verified && this.passwords.has(input.email)) return wait(undefined);
    let user = existing;
    if (!user) {
      user = this.newUser(input.email, false);
      this.users.set(input.email, user);
    }
    user.name = input.name;
    user.phone = input.phone ?? null;
    user.language = input.language;
    user.email_verified = false;
    this.passwords.set(input.email, input.password);
    return wait(undefined);
  }

  async verifyRegister(email: string, code: string): Promise<VerifyResponse> {
    if (!CODE_RE.test(code)) throw new ApiError(400, 'invalid_code');
    const user = this.users.get(email);
    if (!user || !this.passwords.has(email)) throw new ApiError(400, 'invalid_code');
    user.email_verified = true;
    return wait({ session_token: `mock:${email}`, user: clone(user) });
  }

  async loginWithPassword(email: string, password: string): Promise<VerifyResponse> {
    const user = this.users.get(email);
    if (!user || this.passwords.get(email) !== password) throw new ApiError(401, 'wrong email or password');
    if (!user.email_verified) throw new ApiError(403, 'email_not_verified');
    return wait({ session_token: `mock:${email}`, user: clone(user) });
  }

  async getAuthProviders(): Promise<AuthProviders> {
    // Mock mode has no Google OAuth client; Apple works with any token.
    return wait({ google: false, apple: true });
  }

  async signInWithApple(input: AppleSignInInput): Promise<VerifyResponse> {
    const email = 'apple-user@example.com';
    let user = this.users.get(email);
    if (!user) {
      user = this.newUser(email, false);
      user.name = input.name ?? null;
      user.language = input.language;
      this.users.set(email, user);
    }
    user.email_verified = true;
    return wait({ session_token: `mock:${email}`, user: clone(user) });
  }

  async redeemLoginTicket(): Promise<VerifyResponse> {
    throw new ApiError(401, 'invalid ticket');
  }

  async forgotPassword(email: string): Promise<void> {
    if (!EMAIL_RE.test(email)) throw new ApiError(422, 'invalid_email');
    return wait(undefined);
  }

  async resetPassword(email: string, code: string, newPassword: string): Promise<VerifyResponse> {
    if (!CODE_RE.test(code)) throw new ApiError(400, 'invalid_code');
    const user = this.users.get(email);
    if (!user) throw new ApiError(400, 'invalid_code');
    user.email_verified = true;
    this.passwords.set(email, newPassword);
    return wait({ session_token: `mock:${email}`, user: clone(user) });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const user = this.currentUser();
    if (this.passwords.get(user.email) !== currentPassword) throw new ApiError(401, 'wrong current password');
    this.passwords.set(user.email, newPassword);
    return wait(undefined);
  }

  async verifyNotificationEmail(email: string, code: string): Promise<User> {
    const user = this.currentUser();
    if (!EMAIL_RE.test(email)) throw new ApiError(422, 'invalid_email');
    if (!CODE_RE.test(code)) throw new ApiError(400, 'invalid_code');
    user.notification_email = email;
    return wait(clone(user));
  }

  async getMe(): Promise<User> {
    return wait(clone(this.currentUser()));
  }

  async patchMe(patch: UserPatch): Promise<User> {
    const user = this.currentUser();
    Object.assign(user, patch);
    return wait(clone(user));
  }

  async deleteMe(): Promise<void> {
    const user = this.currentUser();
    this.users.delete(user.email);
    this.aois = [];
    this.alerts = [];
    return wait(undefined);
  }

  async registerDevice(): Promise<void> {
    this.currentUser();
    return wait(undefined);
  }

  async getCoverage(): Promise<CoverageResponse> {
    this.currentUser();
    return wait(clone(this.coverage));
  }

  async getNights(): Promise<NightsResponse> {
    this.currentUser();
    return wait({ latest: MOCK_NIGHTS[MOCK_NIGHTS.length - 1], available: [...MOCK_NIGHTS] });
  }

  async getMap(night?: string): Promise<MapResponse> {
    this.currentUser();
    const date = night ?? MOCK_NIGHTS[MOCK_NIGHTS.length - 1];
    if (!MOCK_NIGHTS.includes(date)) throw new ApiError(404, 'night_not_found');
    return wait({
      night_date: date,
      data_source: MOCK_DATA_SOURCE,
      model_version: MOCK_MODEL_VERSION,
      cells: mockCellsFor(date),
    });
  }

  async getPlaceExplanation(pointId: string, night: string, lang: Language): Promise<PlaceExplanation> {
    this.currentUser();
    const cell = mockCellsFor(night).find((c) => c.point_id === pointId);
    if (!cell) throw new ApiError(404, 'unknown_point');
    const pct = Math.round(cell.probability * 100);
    const en = lang === 'en';
    // Mock mode never calls Muse: a fixed template, labeled as such in the app.
    return wait(
      {
        point_id: pointId,
        night_date: night,
        language: en ? 'en' : 'es',
        source: 'template',
        translated: false,
        headline: en ? `Frost risk in ${cell.name}: ${pct}%` : `Riesgo de helada en ${cell.name}: ${pct}%`,
        what_happened: en
          ? `SIMULATED DATA. That night the frost risk in ${cell.name} was ${pct}%.`
          : `DATOS SIMULADOS. Esa noche el riesgo de helada en ${cell.name} fue ${pct}%.`,
        what_next: en
          ? 'Check the official SENAMHI forecast for the next nights.'
          : 'Revise el pronóstico oficial de SENAMHI para las próximas noches.',
        actions: en
          ? ['Cover sensitive crops before dusk.', 'Keep young animals in sheltered corrals.']
          : ['Cubra los cultivos sensibles antes del anochecer.', 'Guarde las crías en corrales protegidos.'],
        sources: [
          { name: 'SENAMHI Bolivia', url: 'https://senamhi.gob.bo', why: en ? 'Official forecast.' : 'Pronóstico oficial.' },
          { name: 'Radio San Gabriel', url: 'https://radiosangabriel.org.bo', why: en ? 'Altiplano news.' : 'Noticias del Altiplano.' },
        ],
      },
      700,
    );
  }

  private withCurrent(aoi: Aoi): Aoi {
    const latest = MOCK_NIGHTS[MOCK_NIGHTS.length - 1];
    const c = centroid(fromPolygon(aoi.polygon));
    let best = { cell: mockCellsFor(latest)[0], km: Infinity };
    for (const cell of mockCellsFor(latest)) {
      const km = haversineKm(c, { latitude: cell.lat, longitude: cell.lon });
      if (km < best.km) best = { cell, km };
    }
    return {
      ...clone(aoi),
      current: {
        night_date: latest,
        probability: best.cell.probability,
        level: best.cell.level,
        cell_used: best.cell.point_id,
        distance_km: Math.round(best.km * 10) / 10,
      },
    };
  }

  async listAois(): Promise<Aoi[]> {
    this.currentUser();
    return wait(this.aois.map((a) => this.withCurrent(a)));
  }

  async createAoi(body: AoiCreate): Promise<Aoi> {
    this.currentUser();
    const points = fromPolygon(body.polygon);
    if (points.length < 3 || points.length > 12) throw new ApiError(422, 'invalid_polygon');
    if (!polygonInsideCoverage(points, this.coverage)) {
      throw new ApiError(422, 'outside_coverage');
    }
    const aoi: Aoi = { id: `aoi-mock-${++this.nextId}`, ...clone(body) };
    this.aois.push(aoi);
    return wait(this.withCurrent(aoi));
  }

  async updateAoi(id: string, patch: AoiPatch): Promise<Aoi> {
    this.currentUser();
    const aoi = this.aois.find((a) => a.id === id);
    if (!aoi) throw new ApiError(404, 'not_found');
    Object.assign(aoi, clone(patch));
    this.alerts.filter((a) => a.aoi_id === id).forEach((a) => (a.aoi_name = aoi.name));
    return wait(this.withCurrent(aoi));
  }

  async deleteAoi(id: string): Promise<void> {
    this.currentUser();
    this.aois = this.aois.filter((a) => a.id !== id);
    return wait(undefined);
  }

  private summary(record: MockAlertRecord): AlertSummary {
    const cell = mockCellsFor(record.night_date).find((c) => c.point_id === record.point_id)!;
    const text = explanationText(this.currentUser().language);
    return {
      id: record.id,
      aoi_id: record.aoi_id,
      aoi_name: record.aoi_name,
      night_date: record.night_date,
      level: cell.level,
      probability: cell.probability,
      channels_sent: [...record.channels_sent],
      sent_at: record.sent_at,
      read: record.read,
      headline: text.headline(record.aoi_name),
      mode: record.mode,
    };
  }

  async listAlerts(): Promise<AlertSummary[]> {
    this.currentUser();
    const list = this.alerts.map((r) => this.summary(r));
    list.sort((a, b) => b.sent_at.localeCompare(a.sent_at));
    return wait(list);
  }

  async getAlert(id: string): Promise<AlertDetail> {
    const record = this.alerts.find((a) => a.id === id);
    if (!record) throw new ApiError(404, 'not_found');
    const cell = mockCellsFor(record.night_date).find((c) => c.point_id === record.point_id)!;
    const text = explanationText(this.currentUser().language);
    const summary = this.summary(record);
    return wait({
      ...summary,
      explanation: {
        headline: summary.headline,
        why: text.why,
        actions: [...text.actions],
        caveats: [...text.caveats],
      },
      conditions_1800: { ...cell.conditions_1800 },
      top_drivers: clone(cell.top_drivers),
      historical_reliability: clone(cell.historical_reliability),
      outcome: cell.observed ? { ...cell.observed } : null,
      model_card_summary: text.summary,
      mode: record.mode,
      explanation_source: record.explanation_source,
    });
  }

  async markAlertRead(id: string): Promise<void> {
    this.currentUser();
    const record = this.alerts.find((a) => a.id === id);
    if (record) record.read = true;
    return wait(undefined);
  }

  async getModelCard(): Promise<ModelCard> {
    this.currentUser();
    return wait(clone(MOCK_MODEL_CARD));
  }
}
