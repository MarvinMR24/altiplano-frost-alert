// Sign in with Google: backend driven OAuth (works in Expo Go and in the Android APK,
// because the app never holds a Google client of its own):
//   1. open `${API_URL}/auth/google/start?redirect=<deep link>` in the system browser
//      (WebBrowser.openAuthSessionAsync);
//   2. the backend finishes OAuth and returns to the deep link with a one-time ticket;
//   3. the app trades the ticket for a session (POST /auth/ticket).
// The Google button is active only when the backend reports it configured (GET /auth/providers).

import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';

import type { Language } from '@/api/types';
import { API_URL } from '@/config';

export class SocialSignInError extends Error {}

// One-time login ticket from the Google flow; null when the user cancels.
export async function googleTicket(language: Language): Promise<string | null> {
  const redirect = Linking.createURL('auth/google');
  const start = `${API_URL}/auth/google/start?redirect=${encodeURIComponent(redirect)}&lang=${language}`;
  const result = await WebBrowser.openAuthSessionAsync(start, redirect);
  if (result.type !== 'success') return null;
  const params = Linking.parse(result.url).queryParams ?? {};
  if (params.error === 'cancelled') return null;
  if (typeof params.ticket !== 'string' || !params.ticket) throw new SocialSignInError('google sign in failed');
  return params.ticket;
}
