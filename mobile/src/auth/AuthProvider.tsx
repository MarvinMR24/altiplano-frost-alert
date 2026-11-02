import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api, ApiError, type User, type UserPatch, type VerifyResponse } from '@/api/client';
import { useI18n } from '@/i18n';
import { clearToken, loadToken, saveToken } from './session';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthValue {
  status: Status;
  user: User | null;
  requestCode: (email: string) => Promise<void>;
  verifyCode: (email: string, code: string) => Promise<void>;
  completeSignIn: (result: VerifyResponse) => Promise<void>;
  updateUser: (patch: UserPatch) => Promise<User>;
  setUser: (user: User) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUserState] = useState<User | null>(null);
  const { setLanguage } = useI18n();

  const setUser = useCallback(
    (next: User) => {
      setUserState(next);
      setLanguage(next.language);
    },
    [setLanguage],
  );

  const signOut = useCallback(async () => {
    await clearToken();
    api.setToken(null);
    setUserState(null);
    setStatus('signedOut');
  }, []);

  // Auto login: restore the stored token and validate it with GET /me.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await loadToken();
      if (!token) {
        if (!cancelled) setStatus('signedOut');
        return;
      }
      api.setToken(token);
      try {
        const me = await api.getMe();
        if (cancelled) return;
        setUser(me);
        setStatus('signedIn');
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) await clearToken();
        api.setToken(null);
        setStatus('signedOut');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setUser]);

  const completeSignIn = useCallback(
    async (result: VerifyResponse) => {
      await saveToken(result.session_token);
      api.setToken(result.session_token);
      setUser(result.user);
      setStatus('signedIn');
    },
    [setUser],
  );

  const requestCode = useCallback((email: string) => api.requestEmailCode(email, 'login'), []);

  const verifyCode = useCallback(
    async (email: string, code: string) => completeSignIn(await api.verifyEmailCode(email, code)),
    [completeSignIn],
  );

  const updateUser = useCallback(
    async (patch: UserPatch) => {
      const next = await api.patchMe(patch);
      setUser(next);
      return next;
    },
    [setUser],
  );

  const value = useMemo<AuthValue>(
    () => ({ status, user, requestCode, verifyCode, completeSignIn, updateUser, setUser, signOut }),
    [status, user, requestCode, verifyCode, completeSignIn, updateUser, setUser, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
