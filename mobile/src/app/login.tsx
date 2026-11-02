import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import { Button, ChipRow, Chip, errorText, Field, styles as ui } from '@/ui/components';
import { spacing } from '@/ui/theme';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen() {
  const { t, language, setLanguage } = useI18n();
  const { requestCode } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setError(t('auth.invalidEmail'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await requestCode(value);
      router.push({ pathname: '/verify', params: { email: value } });
    } catch (err) {
      setError(errorText(t, err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
        <ChipRow>
          <Chip label={t('language.es')} selected={language === 'es'} onPress={() => setLanguage('es')} />
          <Chip label={t('language.en')} selected={language === 'en'} onPress={() => setLanguage('en')} />
        </ChipRow>
        <View style={{ gap: spacing.sm }}>
          <Text style={ui.title}>{t('auth.title')}</Text>
          <Text style={ui.muted}>{t('auth.subtitle')}</Text>
        </View>
        <Field
          label={t('auth.emailLabel')}
          placeholder={t('auth.emailPlaceholder')}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          returnKeyType="send"
          onSubmitEditing={submit}
        />
        {error ? <Text style={ui.errorText}>{error}</Text> : null}
        <Button label={t('auth.sendCode')} onPress={submit} loading={busy} />
        {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
        <Text style={ui.small}>{t('common.reanalysisNote')}</Text>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: 'center' },
});
