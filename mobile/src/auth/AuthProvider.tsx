import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api, ApiError, type EmailCodePurpose, type RegisterInput, type User, type UserPatch, type VerifyResponse } from '@/api/client';
import { useI18n } from '@/i18n';
import { clearToken, loadToken, saveToken } from './session';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthValue {
  status: Status;
  user: User | null;
  requestCode: (email: string, purpose?: EmailCodePurpose) => Promise<void>;
  verifyCode: (email: string, code: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  verifyRegister: (email: string, code: string) => Promise<void>;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (email: string, code: string, newPassword: string) => Promise<void>;
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

  const requestCode = useCallback(
    (email: string, purpose: EmailCodePurpose = 'login') => api.requestEmailCode(email, purpose),
    [],
  );

  const verifyCode = useCallback(
    async (email: string, code: string) => completeSignIn(await api.verifyEmailCode(email, code)),
    [completeSignIn],
  );

  const register = useCallback((input: RegisterInput) => api.register(input), []);

  const verifyRegister = useCallback(
    async (email: string, code: string) => completeSignIn(await api.verifyRegister(email, code)),
    [completeSignIn],
  );

  const loginWithPassword = useCallback(
    async (email: string, password: string) => completeSignIn(await api.loginWithPassword(email, password)),
    [completeSignIn],
  );

  const forgotPassword = useCallback((email: string) => api.forgotPassword(email), []);

  const resetPassword = useCallback(
    async (email: string, code: string, newPassword: string) =>
      completeSignIn(await api.resetPassword(email, code, newPassword)),
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
    () => ({
      status,
      user,
      requestCode,
      verifyCode,
      register,
      verifyRegister,
      loginWithPassword,
      forgotPassword,
      resetPassword,
      completeSignIn,
      updateUser,
      setUser,
      signOut,
    }),
    [
      status,
      user,
      requestCode,
      verifyCode,
      register,
      verifyRegister,
      loginWithPassword,
      forgotPassword,
      resetPassword,
      completeSignIn,
      updateUser,
      setUser,
      signOut,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
