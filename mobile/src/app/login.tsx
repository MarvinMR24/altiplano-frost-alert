import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import { AuthCard, AuthShell, InlineError, OrDivider, PasswordField, SocialButtons } from '@/ui/auth';
import { Button, Field, styles as ui } from '@/ui/components';
import { colors } from '@/ui/theme';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen() {
  const { t } = useI18n();
  const { loginWithPassword, requestCode } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setEmailError(t('auth.invalidEmail'));
      return;
    }
    setEmailError(null);
    setBusy(true);
    setError(null);
    try {
      // On success the auth guard swaps this screen for onboarding or the tabs.
      await loginWithPassword(value, password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError(t('signin.wrongCredentials'));
      else if (err instanceof ApiError && err.status === 403) {
        // The backend already sent a new sign up code; finish verification there.
        router.push({ pathname: '/verify', params: { email: value, purpose: 'register', notice: '1' } });
      }
      else if (err instanceof ApiError && err.status === 429) setError(t('signin.rateLimited'));
      else setError(t('common.networkError'));
      setBusy(false);
    }
  }

  async function signInWithCode() {
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setEmailError(t('auth.invalidEmail'));
      return;
    }
    setEmailError(null);
    setError(null);
    try {
      await requestCode(value);
      router.push({ pathname: '/verify', params: { email: value } });
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t('signin.rateLimited') : t('common.networkError'));
    }
  }

  return (
    <AuthShell title={t('signin.title')} onBack={() => router.back()}>
      <AuthCard>
        <Field
          label={t('auth.emailLabel')}
          icon="mail"
          placeholder={t('auth.emailPlaceholder')}
          value={email}
          onChangeText={setEmail}
          error={emailError}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          returnKeyType="next"
        />
        <PasswordField label={t('auth.passwordLabel')} value={password} onChangeText={setPassword} />
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/forgot')}
          hitSlop={8}
          style={{ alignSelf: 'flex-end' }}
        >
          <Text style={{ color: colors.primary, fontWeight: '600' }}>{t('signin.forgotPassword')}</Text>
        </Pressable>
        <InlineError message={error} />
        <Button label={t('welcome.signIn')} size="large" onPress={submit} loading={busy} />
        {USE_MOCK ? <Text style={ui.small}>{t('auth.mockPasswordHint')}</Text> : null}
        <OrDivider />
        <Button label={t('signin.withCode')} variant="secondary" onPress={signInWithCode} />
        <SocialButtons />
      </AuthCard>
      <View style={{ height: 8 }} />
    </AuthShell>
  );
}
