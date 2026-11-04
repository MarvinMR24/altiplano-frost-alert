// Sign-in providers. Only "email" (6-digit code) is enabled in this version.
//
// Extension point for Google and Apple (later): each provider implements `signIn()` and
// returns a backend session. The planned Google flow is backend driven:
//   1. open `${API_URL}/auth/google/start?redirect=<app deep link>` with
//      WebBrowser.openAuthSessionAsync(url, Linking.createURL('auth/callback'))
//   2. the backend completes OAuth and redirects to the deep link with a one-time code
//   3. the app exchanges that code for `{session_token, user}`
// Apple will follow the same shape. No buttons are shown until a provider is enabled.

import type { VerifyResponse } from '@/api/types';

export type ProviderId = 'email' | 'google' | 'apple';

export interface ExternalAuthProvider {
  id: Exclude<ProviderId, 'email'>;
  enabled: boolean;
  signIn(): Promise<VerifyResponse>;
}

export const externalProviders: ExternalAuthProvider[] = [];

export function enabledExternalProviders(): ExternalAuthProvider[] {
  return externalProviders.filter((p) => p.enabled);
}

// Google and Apple are NOT implemented in this version. The buttons are visual only and
// show a "coming soon" notice. No OAuth code, no client ids, nothing in the backend.
export const SOCIAL_NOT_IMPLEMENTED: Exclude<ProviderId, 'email'>[] = ['google', 'apple'];

export function isSocialImplemented(id: Exclude<ProviderId, 'email'>): boolean {
  return !SOCIAL_NOT_IMPLEMENTED.includes(id) && enabledExternalProviders().some((p) => p.id === id);
}

export function socialComingSoon(): void {
  // Called when a social button is tapped. Sign-in stays disabled on purpose.
}
