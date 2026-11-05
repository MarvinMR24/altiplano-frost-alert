// Deep links that are not screens. The Google sign in returns to
// frostwatch://auth/google?ticket=... (exp://.../--/auth/google in Expo Go); the browser
// session in src/auth/providers.ts reads it, so the router just stays on the home route
// instead of showing "unmatched route".
export function redirectSystemPath({ path }: { path: string; initial: boolean }): string {
  return path.includes('auth/google') ? '/' : path;
}
