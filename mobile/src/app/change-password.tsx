import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, ApiError } from '@/api/client';
import { useI18n } from '@/i18n';
import { InlineError, PasswordField, PasswordMeter, passwordProblem } from '@/ui/auth';
import { Button, styles as ui } from '@/ui/components';
import { haptic } from '@/ui/feedback';
import { Icon } from '@/ui/icons';
import { PopIn } from '@/ui/motion';
import { colors, spacing } from '@/ui/theme';

export default function ChangePasswordScreen() {
  const { t } = useI18n();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit() {
    const problem = passwordProblem(next);
    if (problem) {
      setError(t(problem));
      return;
    }
    if (confirm !== next) {
      setError(t('signup.passwordMismatch'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.changePassword(current, next);
      haptic.success();
      setDone(true);
      setTimeout(() => router.back(), 1200);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError(t('password.wrongCurrent'));
      else setError(t('common.networkError'));
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
      <PasswordField label={t('password.current')} value={current} onChangeText={setCurrent} autoFocus />
      <PasswordField label={t('password.new')} value={next} onChangeText={setNext} />
      <PasswordMeter password={next} />
      <PasswordField label={t('password.confirm')} value={confirm} onChangeText={setConfirm} />
      <InlineError message={error} />
      {done ? (
        <PopIn>
          <View style={styles.done}>
            <Icon name="check-circle" size={28} color={colors.teal} />
            <Text style={[ui.bodyStrong, { color: colors.teal }]}>{t('password.changed')}</Text>
          </View>
        </PopIn>
      ) : null}
      <Button label={t('common.save')} size="large" onPress={submit} loading={busy} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  form: { padding: spacing.xl, gap: spacing.md },
  done: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, justifyContent: 'center' },
});
