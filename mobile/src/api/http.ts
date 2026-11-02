import { API_URL } from '@/config';
import {
  ApiError,
  type AlertDetail,
  type AlertSummary,
  type Aoi,
  type AoiCreate,
  type AoiPatch,
  type Api,
  type CoverageResponse,
  type EmailCodePurpose,
  type MapResponse,
  type ModelCard,
  type NightsResponse,
  type User,
  type UserPatch,
  type VerifyResponse,
} from './types';

// HTTP implementation of docs/api_contract.md.
export class HttpApi implements Api {
  private token: string | null = null;

  constructor(private baseUrl: string = API_URL) {}

  setToken(token: string | null): void {
    this.token = token;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      // Skips the ngrok free-tier interstitial page. Sent on every request.
      'ngrok-skip-browser-warning': '1',
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, 'network');
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
    if (response.status === 204) return undefined as T;
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
