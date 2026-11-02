import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text } from 'react-native';

import { api, ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import { Button, errorText, Field, styles as ui } from '@/ui/components';
import { spacing } from '@/ui/theme';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Changing the notification email re-runs the email code flow (purpose "notification_email").
export default function ChangeEmailScreen() {
  const { t } = useI18n();
  const { setUser } = useAuth();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setError(t('auth.invalidEmail'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.requestEmailCode(value, 'notification_email');
      setEmail(value);
      setSent(true);
    } catch (err) {
      setError(errorText(t, err));
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    if (!/^\d{6}$/.test(code)) {
      setError(t('auth.codeFormat'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setUser(await api.verifyNotificationEmail(email, code));
      router.back();
    } catch (err) {
      const isCodeError = err instanceof ApiError && err.status >= 400 && err.status < 500;
      setError(isCodeError ? t('auth.invalidCode') : errorText(t, err));
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
      {!sent ? (
        <>
          <Field
            label={t('profile.newEmail')}
            placeholder={t('auth.emailPlaceholder')}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoFocus
          />
          {error ? <Text style={ui.errorText}>{error}</Text> : null}
          <Button label={t('auth.sendCode')} onPress={send} loading={busy} />
        </>
      ) : (
        <>
          <Text style={ui.muted}>{t('auth.codeSubtitle', { email })}</Text>
          <Field
            label={t('auth.codeLabel')}
            value={code}
            onChangeText={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
            keyboardType="number-pad"
            textContentType="oneTimeCode"
            maxLength={6}
            autoFocus
          />
          {error ? <Text style={ui.errorText}>{error}</Text> : null}
          <Button label={t('auth.verify')} onPress={verify} loading={busy} />
          {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
        </>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.xl, gap: spacing.lg },
});
