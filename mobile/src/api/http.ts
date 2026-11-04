import { API_URL } from '@/config';
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
  type EmailCodePurpose,
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

const REQUEST_TIMEOUT_MS = 12000;
// Muse reasons before it answers: a place explanation can take close to a minute.
const EXPLAIN_TIMEOUT_MS = 150000;

// HTTP implementation of docs/api_contract.md.
export class HttpApi implements Api {
  private token: string | null = null;

  constructor(private baseUrl: string = API_URL) {}

  setToken(token: string | null): void {
    this.token = token;
  }

  private async request<T>(method: string, path: string, body?: unknown, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    // Without a timeout an unreachable backend (for example after the laptop changed
    // Wi-Fi and its IP) leaves the app on the loading screen forever.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError(0, 'network');
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = (await response.json()) as { detail?: unknown };
        if (typeof data.detail === 'string') detail = data.detail;
      } catch {
        // Non-JSON error body; keep the status text.
      }
      throw new ApiError(response.status, detail);
    }
    if (response.status === 204 || response.status === 202) return undefined as T;
    return (await response.json()) as T;
  }

  requestEmailCode(email: string, purpose: EmailCodePurpose = 'login'): Promise<void> {
    return this.request('POST', '/auth/email/request', { email, purpose });
  }

  verifyEmailCode(email: string, code: string): Promise<VerifyResponse> {
    return this.request('POST', '/auth/email/verify', { email, code, purpose: 'login' });
  }

  async verifyNotificationEmail(email: string, code: string): Promise<User> {
    const result = await this.request<{ user: User }>('POST', '/auth/email/verify', {
      email,
      code,
      purpose: 'notification_email',
    });
    return result.user;
  }

  register(input: RegisterInput): Promise<void> {
    return this.request('POST', '/auth/register', input);
  }

  verifyRegister(email: string, code: string): Promise<VerifyResponse> {
    return this.request('POST', '/auth/email/verify', { email, code, purpose: 'register' });
  }

  loginWithPassword(email: string, password: string): Promise<VerifyResponse> {
    return this.request('POST', '/auth/login', { email, password });
  }

  getAuthProviders(): Promise<AuthProviders> {
    return this.request('GET', '/auth/providers');
  }

  signInWithApple(input: AppleSignInInput): Promise<VerifyResponse> {
    return this.request('POST', '/auth/apple', input);
  }

  redeemLoginTicket(ticket: string): Promise<VerifyResponse> {
    return this.request('POST', '/auth/ticket', { ticket });
  }

  forgotPassword(email: string): Promise<void> {
    return this.request('POST', '/auth/password/forgot', { email });
  }

  resetPassword(email: string, code: string, newPassword: string): Promise<VerifyResponse> {
    return this.request('POST', '/auth/password/reset', { email, code, new_password: newPassword });
  }

  changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return this.request('POST', '/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  getMe(): Promise<User> {
    return this.request('GET', '/me');
  }

  patchMe(patch: UserPatch): Promise<User> {
    return this.request('PATCH', '/me', patch);
  }

  deleteMe(): Promise<void> {
    return this.request('DELETE', '/me');
  }

  registerDevice(expoPushToken: string): Promise<void> {
    return this.request('POST', '/devices', { expo_push_token: expoPushToken });
  }

  getCoverage(): Promise<CoverageResponse> {
    return this.request('GET', '/coverage');
  }

  getNights(): Promise<NightsResponse> {
    return this.request('GET', '/nights');
  }

  getMap(night?: string): Promise<MapResponse> {
    const query = night ? `?night=${encodeURIComponent(night)}` : '';
    return this.request('GET', `/map${query}`);
  }

  getPlaceExplanation(pointId: string, night: string, lang: Language): Promise<PlaceExplanation> {
    const query = `?night=${encodeURIComponent(night)}&lang=${lang}`;
    return this.request('GET', `/map/${encodeURIComponent(pointId)}/explain${query}`, undefined, EXPLAIN_TIMEOUT_MS);
  }

  listAois(): Promise<Aoi[]> {
    return this.request('GET', '/aois');
  }

  createAoi(body: AoiCreate): Promise<Aoi> {
    return this.request('POST', '/aois', body);
  }

  updateAoi(id: string, patch: AoiPatch): Promise<Aoi> {
    return this.request('PATCH', `/aois/${encodeURIComponent(id)}`, patch);
  }

  deleteAoi(id: string): Promise<void> {
    return this.request('DELETE', `/aois/${encodeURIComponent(id)}`);
  }

  listAlerts(): Promise<AlertSummary[]> {
    return this.request('GET', '/alerts');
  }

  getAlert(id: string): Promise<AlertDetail> {
    return this.request('GET', `/alerts/${encodeURIComponent(id)}`);
  }

  markAlertRead(id: string): Promise<void> {
    return this.request('POST', `/alerts/${encodeURIComponent(id)}/read`);
  }

  getModelCard(): Promise<ModelCard> {
    return this.request('GET', '/model-card');
  }
}
