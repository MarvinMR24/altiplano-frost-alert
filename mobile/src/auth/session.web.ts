// Web build (local testing only): expo-secure-store has no web implementation, so the
// session token lives in localStorage. Native builds use ./session.ts.
const TOKEN_KEY = 'frostwatch.session_token';

export async function loadToken(): Promise<string | null> {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function saveToken(token: string): Promise<void> {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage blocked (private mode): the session lasts until the tab closes.
  }
}

export async function clearToken(): Promise<void> {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing stored.
  }
}
