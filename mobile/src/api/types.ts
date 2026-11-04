// Types mirroring docs/api_contract.md. Keep both in sync.

export type Level = 'low' | 'moderate' | 'high' | 'very_high';
export type Language = 'es' | 'en' | 'ay' | 'qu';
export type ProfileType = 'producer' | 'resident';
export type Threshold = 30 | 50 | 70;
export type Channel = 'push' | 'email';

export interface User {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  email_verified: boolean;
  language: Language;
  profile: ProfileType;
  crops: string[];
  livestock: string[];
  default_threshold: Threshold;
  notification_email: string;
  onboarded: boolean;
}

export type UserPatch = Partial<
  Pick<User, 'name' | 'language' | 'profile' | 'crops' | 'livestock' | 'default_threshold' | 'onboarded'>
>;

export interface Driver {
  feature: string;
  effect: 'up' | 'down';
  weight: number;
}

export interface Reliability {
  range: [number, number];
  observed_rate: number;
  n: number;
}

export type Conditions1800 = Record<string, number>;

export interface Observed {
  frost: boolean;
  tmin_c: number;
}

export interface Cell {
  point_id: string;
  name: string;
  lat: number;
  lon: number;
  elevation_m: number;
  probability: number;
  level: Level;
  top_drivers: Driver[];
  conditions_1800: Conditions1800;
  historical_reliability: Reliability;
  observed?: Observed;
}

export interface MapResponse {
  night_date: string;
  data_source: string;
  model_version: string;
  cells: Cell[];
}

export interface NightsResponse {
  latest: string;
  available: string[];
}

// GeoJSON positions are [lon, lat].
export type Position = [number, number];

export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: Position[][];
}

// Which social sign in options the backend has configured.
export interface AuthProviders {
  google: boolean;
  apple: boolean;
}

export interface AppleSignInInput {
  identity_token: string;
  name?: string;
  language: Language;
}

// Plain explanation of one place and night, written by Muse on request (or the template).
export interface PlaceExplanation {
  point_id: string;
  night_date: string;
  language: Language;
  source: 'muse' | 'template';
  // True when the text is a Muse translation of the Spanish base explanation.
  translated: boolean;
  headline: string;
  what_happened: string;
  what_next: string;
  actions: string[];
  sources: { name: string; url: string; why: string }[];
}

export interface CoverageFeature {
  type: 'Feature';
  geometry: PolygonGeometry;
  properties: { point_id: string; name: string };
}

export interface CoverageResponse {
  type: 'FeatureCollection';
  features: CoverageFeature[];
  meta: { radius_km: number };
}

export interface Channels {
  push: boolean;
  email: boolean;
}

export interface AoiCurrent {
  night_date: string;
  probability: number;
  level: Level;
  cell_used: string;
  distance_km: number;
}

export interface Aoi {
  id: string;
  name: string;
  polygon: PolygonGeometry;
  threshold: Threshold;
  channels: Channels;
  current?: AoiCurrent;
}

export interface AoiCreate {
  name: string;
  polygon: PolygonGeometry;
  threshold: Threshold;
  channels: Channels;
}

export type AoiPatch = Partial<Pick<Aoi, 'name' | 'threshold' | 'channels'>>;

export interface AlertSummary {
  id: string;
  aoi_id: string;
  aoi_name: string;
  night_date: string;
  level: Level;
  probability: number;
  channels_sent: Channel[];
  sent_at: string;
  read: boolean;
  headline: string;
  mode?: 'replay' | 'tick' | string;
}

export interface Explanation {
  headline: string;
  why: string;
  actions: string[];
  caveats: string[];
}

export interface AlertDetail extends AlertSummary {
  explanation: Explanation;
  conditions_1800: Conditions1800;
  top_drivers: Driver[];
  historical_reliability: Reliability;
  outcome: Observed | null;
  model_card_summary: string;
  data_source?: string;
  mode?: 'replay' | 'tick' | string;
  explanation_source?: 'muse' | 'template';
}

export interface Metrics {
  pr_auc: number;
  f2: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  brier: number;
  accuracy: number;
  majority_accuracy: number;
}

export interface ModelCard {
  model_version: string;
  trained_years: [number, number];
  n_cells: number;
  metrics: { validation: Metrics; test: Metrics };
  limitations: string[];
}

export interface VerifyResponse {
  session_token: string;
  user: User;
}

export type EmailCodePurpose = 'login' | 'notification_email' | 'register';

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  phone?: string;
  language: Language;
}

export interface Api {
  setToken(token: string | null): void;
  requestEmailCode(email: string, purpose?: EmailCodePurpose): Promise<void>;
  verifyEmailCode(email: string, code: string): Promise<VerifyResponse>;
  verifyNotificationEmail(email: string, code: string): Promise<User>;
  register(input: RegisterInput): Promise<void>;
  verifyRegister(email: string, code: string): Promise<VerifyResponse>;
  loginWithPassword(email: string, password: string): Promise<VerifyResponse>;
  getAuthProviders(): Promise<AuthProviders>;
  signInWithApple(input: AppleSignInInput): Promise<VerifyResponse>;
  redeemLoginTicket(ticket: string): Promise<VerifyResponse>;
  forgotPassword(email: string): Promise<void>;
  resetPassword(email: string, code: string, newPassword: string): Promise<VerifyResponse>;
  changePassword(currentPassword: string, newPassword: string): Promise<void>;
  getMe(): Promise<User>;
  patchMe(patch: UserPatch): Promise<User>;
  deleteMe(): Promise<void>;
  registerDevice(expoPushToken: string): Promise<void>;
  getCoverage(): Promise<CoverageResponse>;
  getNights(): Promise<NightsResponse>;
  getMap(night?: string): Promise<MapResponse>;
  getPlaceExplanation(pointId: string, night: string, lang: Language): Promise<PlaceExplanation>;
  listAois(): Promise<Aoi[]>;
  createAoi(body: AoiCreate): Promise<Aoi>;
  updateAoi(id: string, patch: AoiPatch): Promise<Aoi>;
  deleteAoi(id: string): Promise<void>;
  listAlerts(): Promise<AlertSummary[]>;
  getAlert(id: string): Promise<AlertDetail>;
  markAlertRead(id: string): Promise<void>;
  getModelCard(): Promise<ModelCard>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
