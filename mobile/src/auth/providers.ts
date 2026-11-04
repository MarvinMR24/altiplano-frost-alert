// Social sign in. Both work in Expo Go:
//
// Apple (iOS only): the native Apple sheet returns an identity token signed by Apple; the
// backend verifies it (POST /auth/apple). Android and the web have no native Apple sign in,
// so the button is hidden there.
//
// Google: backend driven OAuth, because Expo Go cannot register its own Google client:
//   1. open `${API_URL}/auth/google/start?redirect=<deep link>` in the system browser
//      (WebBrowser.openAuthSessionAsync);
//   2. the backend finishes OAuth and returns to the deep link with a one-time ticket;
//   3. the app trades the ticket for a session (POST /auth/ticket).
// The Google button is active only when the backend reports it configured (GET /auth/providers).

import * as AppleAuthentication from 'expo-apple-authentication';
import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';
import { Platform } from 'react-native';

import type { Language } from '@/api/types';
import { API_URL } from '@/config';

export class SocialSignInError extends Error {}

export async function appleSignInAvailable(): Promise<boolean> {
  if (Platform.OS !== 'ios') return false;
  try {
    return await AppleAuthentication.isAvailableAsync();
  } catch {
    return false;
  }
}

// Identity token and (first time only) the name; null when the user cancels.
export async function appleCredential(): Promise<{ identityToken: string; name?: string } | null> {
  try {
    const credential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
    });
    if (!credential.identityToken) throw new SocialSignInError('no identity token');
    const parts = [credential.fullName?.givenName, credential.fullName?.familyName].filter(Boolean);
    return { identityToken: credential.identityToken, name: parts.length ? parts.join(' ') : undefined };
  } catch (err) {
    if ((err as { code?: string }).code === 'ERR_REQUEST_CANCELED') return null;
    throw err instanceof SocialSignInError ? err : new SocialSignInError('apple sign in failed');
  }
}

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
