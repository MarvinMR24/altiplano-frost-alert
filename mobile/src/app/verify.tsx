import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import { Button, errorText, Field, styles as ui } from '@/ui/components';
import { spacing } from '@/ui/theme';

export default function VerifyScreen() {
  const { email = '' } = useLocalSearchParams<{ email: string }>();
  const { t } = useI18n();
  const { verifyCode, requestCode } = useAuth();
  const [code, setCode] = useState('');
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!/^\d{6}$/.test(code)) {
      setMessage({ text: t('auth.codeFormat'), error: true });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      // On success the auth guard swaps this screen for onboarding or the tabs.
      await verifyCode(email, code);
    } catch (err) {
      const isCodeError = err instanceof ApiError && err.status >= 400 && err.status < 500;
      setMessage({ text: isCodeError ? t('auth.invalidCode') : errorText(t, err), error: true });
      setBusy(false);
    }
  }

  async function resend() {
    try {
      await requestCode(email);
      setMessage({ text: t('auth.codeResent'), error: false });
    } catch (err) {
      setMessage({ text: errorText(t, err), error: true });
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
      <View style={{ gap: spacing.sm }}>
        <Text style={ui.title}>{t('auth.codeTitle')}</Text>
        <Text style={ui.muted}>{t('auth.codeSubtitle', { email })}</Text>
      </View>
      <Field
        label={t('auth.codeLabel')}
        value={code}
        onChangeText={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="one-time-code"
        maxLength={6}
        style={styles.code}
        autoFocus
      />
      {message ? <Text style={message.error ? ui.errorText : ui.muted}>{message.text}</Text> : null}
      <Button label={t('auth.verify')} onPress={submit} loading={busy} />
      <Button label={t('auth.resend')} onPress={resend} variant="secondary" />
      <Button label={t('auth.changeEmail')} onPress={() => router.back()} variant="secondary" />
      {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: 'center' },
  code: { fontSize: 28, letterSpacing: 8, textAlign: 'center' },
});
