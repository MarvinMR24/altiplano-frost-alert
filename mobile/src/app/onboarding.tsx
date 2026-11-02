import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, type ProfileType } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { CROPS, LIVESTOCK, toggle } from '@/constants';
import { useI18n } from '@/i18n';
import { getExpoPushToken, requestPushPermission, type PushPermission } from '@/notifications/push';
import { Button, Chip, ChipRow, errorText, SectionTitle, styles as ui } from '@/ui/components';
import { colors, spacing } from '@/ui/theme';

const TOTAL_STEPS = 4;

export default function OnboardingScreen() {
  const { t, language, setLanguage } = useI18n();
  const { user, updateUser } = useAuth();
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<ProfileType>(user?.profile ?? 'producer');
  const [crops, setCrops] = useState<string[]>(user?.crops ?? []);
  const [livestock, setLivestock] = useState<string[]>(user?.livestock ?? []);
  const [permission, setPermission] = useState<PushPermission | null>(null);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enableNotifications() {
    setAsking(true);
    const result = await requestPushPermission();
    setPermission(result);
    if (result === 'granted') {
      const token = await getExpoPushToken();
      if (token) {
        try {
          await api.registerDevice(token);
        } catch (err) {
          console.warn('POST /devices failed', err);
        }
      }
    }
    setAsking(false);
  }

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      // Flipping `onboarded` makes the root guard show the tabs.
      await updateUser({ language, profile, crops, livestock, onboarded: true });
    } catch (err) {
      setError(errorText(t, err));
      setBusy(false);
    }
  }

  const permissionText: Record<PushPermission, string> = {
    granted: t('onboarding.notificationsEnabled'),
    denied: t('onboarding.notificationsDenied'),
    unavailable: t('onboarding.notificationsUnavailable'),
  };

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={ui.small}>{t('onboarding.step', { n: step + 1, total: TOTAL_STEPS })}</Text>

        {step === 0 && (
          <View style={styles.section}>
            <Text style={ui.title}>{t('onboarding.languageTitle')}</Text>
            <ChipRow>
              <Chip label={t('language.es')} selected={language === 'es'} onPress={() => setLanguage('es')} />
              <Chip label={t('language.en')} selected={language === 'en'} onPress={() => setLanguage('en')} />
            </ChipRow>
          </View>
        )}

        {step === 1 && (
          <View style={styles.section}>
            <Text style={ui.title}>{t('onboarding.profileTitle')}</Text>
            {(['producer', 'resident'] as const).map((p) => (
              <Pressable
                key={p}
                accessibilityRole="button"
                accessibilityState={{ selected: profile === p }}
                onPress={() => setProfile(p)}
                style={[styles.option, profile === p && styles.optionSelected]}
              >
                <Text style={ui.bodyStrong}>{t(`onboarding.${p}`)}</Text>
                <Text style={ui.muted}>{t(`onboarding.${p}Desc`)}</Text>
              </Pressable>
            ))}
          </View>
        )}

        {step === 2 && (
          <View style={styles.section}>
            <Text style={ui.title}>{t('onboarding.cropsTitle')}</Text>
            <SectionTitle>{t('onboarding.cropsLabel')}</SectionTitle>
            <ChipRow>
              {CROPS.map((c) => (
                <Chip key={c} label={t(`crop.${c}`)} selected={crops.includes(c)} onPress={() => setCrops(toggle(crops, c))} />
              ))}
            </ChipRow>
            <SectionTitle>{t('onboarding.livestockLabel')}</SectionTitle>
            <ChipRow>
              {LIVESTOCK.map((l) => (
                <Chip
                  key={l}
                  label={t(`livestock.${l}`)}
                  selected={livestock.includes(l)}
                  onPress={() => setLivestock(toggle(livestock, l))}
                />
              ))}
            </ChipRow>
          </View>
        )}

        {step === 3 && (
          <View style={styles.section}>
            <Text style={ui.title}>{t('onboarding.notificationsTitle')}</Text>
            <Text style={ui.body}>{t('onboarding.notificationsBody')}</Text>
            {permission ? (
              <Text style={permission === 'granted' ? ui.body : ui.muted}>{permissionText[permission]}</Text>
            ) : (
              <Button label={t('onboarding.enableNotifications')} onPress={enableNotifications} loading={asking} />
            )}
            <Text style={ui.muted}>{t('onboarding.emailNote', { email: user?.notification_email ?? user?.email ?? '' })}</Text>
          </View>
        )}

        {error ? <Text style={ui.errorText}>{error}</Text> : null}

        <View style={styles.nav}>
          {step > 0 ? (
            <Button label={t('common.back')} onPress={() => setStep(step - 1)} variant="secondary" style={{ flex: 1 }} />
          ) : null}
          {step < TOTAL_STEPS - 1 ? (
            <Button label={t('common.next')} onPress={() => setStep(step + 1)} style={{ flex: 1 }} />
          ) : (
            <Button label={t('onboarding.finish')} onPress={finish} loading={busy} style={{ flex: 1 }} />
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: 'center' },
  section: { gap: spacing.md },
  option: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: spacing.lg,
    gap: spacing.xs,
    backgroundColor: colors.surface,
  },
  optionSelected: { borderColor: colors.primary, borderWidth: 2 },
  nav: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.lg },
});
