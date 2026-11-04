import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import { AuthCard, AuthShell, CodeInput, InlineError, useCountdown } from '@/ui/auth';
import { Button, styles as ui } from '@/ui/components';

export default function VerifyScreen() {
  const { email = '', purpose, notice } = useLocalSearchParams<{ email: string; purpose?: string; notice?: string }>();
  const isRegister = purpose === 'register';
  const { t } = useI18n();
  const { verifyCode, verifyRegister, requestCode } = useAuth();
  const [code, setCode] = useState('');
  const [message, setMessage] = useState<string | null>(notice ? t('signin.notVerified') : null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const countdown = useCountdown(60, email);

  async function submit(value: string = code) {
    if (!/^\d{6}$/.test(value)) {
      setError(t('auth.codeFormat'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // On success the auth guard swaps this screen for onboarding or the tabs.
      await (isRegister ? verifyRegister(email, value) : verifyCode(email, value));
    } catch (err) {
      const isCodeError = err instanceof ApiError && err.status >= 400 && err.status < 500;
      setError(isCodeError ? t('auth.invalidCode') : t('common.networkError'));
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await requestCode(email, isRegister ? 'register' : 'login');
      countdown.restart();
      setMessage(t('auth.codeResent'));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t('signin.rateLimited') : t('common.networkError'));
    }
  }

  return (
    <AuthShell title={t('auth.codeTitle')} subtitle={t('auth.codeSubtitle', { email })} onBack={() => router.back()}>
      <AuthCard>
        <CodeInput value={code} onChange={setCode} onComplete={submit} />
        <InlineError message={error} />
        {message ? <Text style={[ui.muted, { textAlign: 'center' }]}>{message}</Text> : null}
        <Button label={t('auth.verify')} size="large" onPress={() => submit()} loading={busy} />
        {countdown.left > 0 ? (
          <Text style={[ui.small, { textAlign: 'center' }]}>{t('auth.resendIn', { s: countdown.left })}</Text>
        ) : (
          <Button label={t('auth.resend')} variant="secondary" onPress={resend} />
        )}
        <Button label={t('auth.changeEmail')} variant="secondary" onPress={() => router.back()} />
        {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
      </AuthCard>
    </AuthShell>
  );
}
