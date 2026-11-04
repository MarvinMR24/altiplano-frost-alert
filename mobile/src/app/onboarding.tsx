import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, type ProfileType, type Threshold } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { CROPS } from '@/catalog/crops';
import { LIVESTOCK } from '@/catalog/livestock';
import { useI18n } from '@/i18n';
import { getExpoPushToken, requestPushPermission, type PushPermission } from '@/notifications/push';
import { StepProgress, StepSlide } from '@/ui/auth';
import { CatalogPicker } from '@/ui/CatalogPicker';
import { haptic } from '@/ui/feedback';
import { Button, Card, errorText, SectionTitle, styles as ui } from '@/ui/components';
import { Icon } from '@/ui/icons';
import { Logo } from '@/ui/logo';
import { FadeIn, PopIn } from '@/ui/motion';
import { ThresholdField } from '@/ui/ThresholdField';
import { colors, spacing } from '@/ui/theme';

const SUB_STEPS = 3;

export default function OnboardingScreen() {
  const { t } = useI18n();
  const { user, updateUser } = useAuth();
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<ProfileType>(user?.profile ?? 'producer');
  const [crops, setCrops] = useState<string[]>(user?.crops ?? []);
  const [livestock, setLivestock] = useState<string[]>(user?.livestock ?? []);
  const [threshold, setThreshold] = useState<Threshold>(user?.default_threshold ?? 50);
  const [permission, setPermission] = useState<PushPermission | null>(null);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [succeeded, setSucceeded] = useState(false);

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

  async function saveAndContinue() {
    setBusy(true);
    setError(null);
    try {
      await updateUser({ profile, crops, livestock, default_threshold: threshold });
      setStep(step + 1);
    } catch (err) {
      setError(errorText(t, err));
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      await updateUser({ profile, crops, livestock, default_threshold: threshold });
      haptic.success();
      setSucceeded(true);
    } catch (err) {
      setError(errorText(t, err));
    } finally {
      setBusy(false);
    }
  }

  async function goToMap() {
    setBusy(true);
    try {
      // Flipping `onboarded` makes the root guard show the tabs.
      await updateUser({ onboarded: true });
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

  if (succeeded) {
    return (
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.success}>
          <PopIn>
            <View style={styles.successBadge}>
              <Icon name="check-circle" size={72} color={colors.teal} />
            </View>
          </PopIn>
          <FadeIn delay={200} style={{ alignItems: 'center', gap: spacing.sm }}>
            <Text style={ui.title}>{t('signup.successTitle')}</Text>
            <Text style={ui.muted}>{t('signup.successBody')}</Text>
          </FadeIn>
          {error ? <Text style={ui.errorText}>{error}</Text> : null}
          <FadeIn delay={380} style={{ alignSelf: 'stretch' }}>
            <Button label={t('signup.goToMap')} icon="map" size="large" onPress={goToMap} loading={busy} />
          </FadeIn>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={{ alignItems: 'center' }}>
          <Logo size={56} />
        </View>
        <StepProgress step={step + 1} total={SUB_STEPS} />

        <StepSlide stepKey={step}>
          {step === 0 && (
            <View style={styles.section}>
              <Text style={ui.title}>{t('onboarding.profileTitle')}</Text>
              {(['producer', 'resident'] as const).map((p) => (
                <Pressable
                  key={p}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: profile === p }}
                  onPress={() => {
                    haptic.select();
                    setProfile(p);
                  }}
                  style={({ pressed }) => [styles.option, profile === p && styles.optionSelected, pressed && { opacity: 0.8 }]}
                >
                  <View style={[styles.optionIcon, profile === p && styles.optionIconSelected]}>
                    <Icon name={p} size={34} color={profile === p ? colors.primaryText : colors.primary} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[ui.bodyStrong, { fontSize: 18 }]}>{t(`onboarding.${p}`)}</Text>
                    <Text style={[ui.muted, { textAlign: 'left' }]}>{t(`onboarding.${p}Desc`)}</Text>
                  </View>
                  {profile === p ? <Icon name="check-circle" size={26} color={colors.primary} /> : null}
                </Pressable>
              ))}
            </View>
          )}

          {step === 1 && (
            <View style={styles.section}>
              <Text style={ui.title}>{t(profile === 'producer' ? 'onboarding.cropsTitle' : 'onboarding.alertsTitle')}</Text>
              {profile === 'producer' ? (
                <>
                  <SectionTitle>{t('onboarding.cropsLabel')}</SectionTitle>
                  <CatalogPicker
                    title={t('onboarding.cropsLabel')}
                    catalog={CROPS}
                    selected={crops}
                    onChange={setCrops}
                    placeholder={t('picker.search')}
                  />
                  <SectionTitle>{t('onboarding.livestockLabel')}</SectionTitle>
                  <CatalogPicker
                    title={t('onboarding.livestockLabel')}
                    catalog={LIVESTOCK}
                    selected={livestock}
                    onChange={setLivestock}
                    placeholder={t('picker.search')}
                  />
                </>
              ) : null}
              <ThresholdField value={threshold} onChange={setThreshold} />
            </View>
          )}

          {step === 2 && (
            <View style={styles.section}>
              <Text style={ui.title}>{t('onboarding.notificationsTitle')}</Text>
              <Card>
                <View style={styles.explainRow}>
                  <Icon name="bell" size={24} color={colors.primary} />
                  <Text style={[ui.body, { flex: 1 }]}>{t('onboarding.notificationsBody')}</Text>
                </View>
              </Card>
              {permission ? (
                <Text style={permission === 'granted' ? ui.body : ui.muted}>{permissionText[permission]}</Text>
              ) : (
                <Button label={t('onboarding.enableNotifications')} icon="bell" size="large" onPress={enableNotifications} loading={asking} />
              )}
              <Text style={ui.muted}>{t('onboarding.emailNote', { email: user?.notification_email ?? user?.email ?? '' })}</Text>
            </View>
          )}
        </StepSlide>

        {error ? <Text style={ui.errorText}>{error}</Text> : null}

        <View style={styles.nav}>
          {step > 0 ? (
            <Button label={t('common.back')} onPress={() => setStep(step - 1)} variant="secondary" style={{ flex: 1 }} />
          ) : null}
          {step < SUB_STEPS - 1 ? (
            <Button label={t('common.next')} onPress={saveAndContinue} loading={busy} style={{ flex: 1 }} />
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
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    minHeight: 88,
  },
  optionSelected: { borderColor: colors.primary, borderWidth: 3, backgroundColor: colors.beige },
  optionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.navButtonBg,
  },
  optionIconSelected: { backgroundColor: colors.primary },
  successBadge: {
    width: 120,
    height: 120,
    borderRadius: 60,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderWidth: 3,
    borderColor: colors.teal,
  },
  explainRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  nav: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.lg },
  success: { flex: 1, padding: spacing.xl, gap: spacing.lg, alignItems: 'center', justifyContent: 'center' },
});
