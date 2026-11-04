import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { useI18n } from '@/i18n';
import {
  AuthCard,
  AuthShell,
  CodeInput,
  InlineError,
  PasswordField,
  PasswordMeter,
  passwordProblem,
  StepProgress,
  StepSlide,
  useCountdown,
} from '@/ui/auth';
import { Button, Field, styles as ui } from '@/ui/components';
import { colors, spacing } from '@/ui/theme';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^[+\d][+\d ]*$/;
const TOTAL_STEPS = 4;

export default function SignupScreen() {
  const { t, language } = useI18n();
  const { register, verifyRegister, requestCode } = useAuth();
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [code, setCode] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const countdown = useCountdown(60, step);

  const titles = { 1: t('signup.aboutYou'), 2: t('signup.account'), 3: t('signup.verifyEmail'), 4: t('signup.profile') };

  function fail(message: string) {
    setError(message);
    setBusy(false);
  }

  function nextFromAbout() {
    const errors: Record<string, string> = {};
    if (name.trim().length < 2 || name.trim().length > 80) errors.name = t('signup.nameLength');
    const digits = phone.trim();
    if (digits && (digits.length < 6 || digits.length > 20 || !PHONE_RE.test(digits))) {
      errors.phone = t('signup.phoneInvalid');
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length === 0) {
      setError(null);
      setStep(2);
    }
  }

  async function nextFromAccount() {
    const errors: Record<string, string> = {};
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) errors.email = t('auth.invalidEmail');
    const problem = passwordProblem(password);
    if (problem) errors.password = t(problem);
    if (confirm !== password) errors.confirm = t('signup.passwordMismatch');
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setBusy(true);
    setError(null);
    try {
      await register({ name: name.trim(), email: value, password, phone: phone.trim() || undefined, language });
      setEmail(value);
      setStep(3);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) fail(t('signin.rateLimited'));
      else if (err instanceof ApiError && err.status >= 400 && err.status < 500) fail(t('auth.invalidEmail'));
      else fail(t('common.networkError'));
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(value: string = code) {
    if (!/^\d{6}$/.test(value)) {
      setError(t('auth.codeFormat'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // On success the auth guard swaps this screen for onboarding (step 4).
      await verifyRegister(email, value);
    } catch (err) {
      const isCodeError = err instanceof ApiError && err.status >= 400 && err.status < 500;
      fail(isCodeError ? t('auth.invalidCode') : t('common.networkError'));
    }
  }

  async function resend() {
    setError(null);
    try {
      await requestCode(email, 'register');
      countdown.restart();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t('signin.rateLimited') : t('common.networkError'));
    }
  }

  return (
    <AuthShell
      title={titles[step as 1 | 2 | 3]}
      onBack={() => (step === 1 ? router.back() : setStep(step - 1))}
    >
      <StepProgress step={step} total={TOTAL_STEPS} />
      <StepSlide stepKey={step}>
        {step === 1 && (
          <AuthCard>
            <Field
              label={t('signup.nameLabel')}
              icon="user"
              placeholder={t('signup.namePlaceholder')}
              value={name}
              onChangeText={setName}
              error={fieldErrors.name}
              maxLength={80}
              autoFocus
              returnKeyType="next"
            />
            <Field
              label={t('signup.phoneLabel')}
              icon="phone"
              placeholder={t('signup.phonePlaceholder')}
              value={phone}
              onChangeText={setPhone}
              error={fieldErrors.phone}
              keyboardType="phone-pad"
              textContentType="telephoneNumber"
              maxLength={20}
              returnKeyType="next"
            />
            <InlineError message={error} />
            <Button label={t('common.next')} size="large" onPress={nextFromAbout} />
          </AuthCard>
        )}
        {step === 2 && (
          <AuthCard>
            <Field
              label={t('auth.emailLabel')}
              icon="mail"
              placeholder={t('auth.emailPlaceholder')}
              value={email}
              onChangeText={setEmail}
              error={fieldErrors.email}
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
              returnKeyType="next"
            />
            <PasswordField label={t('signup.passwordLabel')} value={password} onChangeText={setPassword} error={fieldErrors.password} />
            <PasswordMeter password={password} />
            <PasswordField
              label={t('signup.confirmPassword')}
              value={confirm}
              onChangeText={setConfirm}
              error={fieldErrors.confirm}
            />
            {USE_MOCK ? <Text style={ui.small}>{t('auth.mockPasswordHint')}</Text> : null}
            <InlineError message={error} />
            <Button label={t('common.next')} size="large" onPress={nextFromAccount} loading={busy} />
          </AuthCard>
        )}
        {step === 3 && (
          <AuthCard>
            <Text style={ui.muted}>{t('auth.codeSubtitle', { email })}</Text>
            <CodeInput value={code} onChange={setCode} onComplete={submitCode} />
            <InlineError message={error} />
            <Button label={t('auth.verify')} size="large" onPress={() => submitCode()} loading={busy} />
            {countdown.left > 0 ? (
              <Text style={[ui.small, { textAlign: 'center' }]}>{t('auth.resendIn', { s: countdown.left })}</Text>
            ) : (
              <Button label={t('auth.resend')} variant="secondary" onPress={resend} />
            )}
            <Button label={t('auth.changeEmail')} variant="secondary" onPress={() => setStep(2)} />
            {/* Shown to everyone: the backend sends no code to an already verified email and
                must not reveal that, so the way out is always visible. */}
            <View style={styles.help}>
              <Text style={[ui.small, { fontSize: 14 }]}>{t('signup.codeHelp')}</Text>
              <View style={styles.helpRow}>
                <Pressable accessibilityRole="button" onPress={() => router.replace('/login')} hitSlop={8}>
                  <Text style={styles.link}>{t('welcome.signIn')}</Text>
                </Pressable>
                <Pressable accessibilityRole="button" onPress={() => router.replace('/forgot')} hitSlop={8}>
                  <Text style={styles.link}>{t('signin.forgotPassword')}</Text>
                </Pressable>
              </View>
            </View>
            {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
          </AuthCard>
        )}
      </StepSlide>
      <View style={{ height: spacing.md }} />
    </AuthShell>
  );
}

const styles = StyleSheet.create({
  help: { gap: spacing.sm, paddingTop: spacing.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  helpRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg },
  link: { color: colors.primary, fontWeight: '700', fontSize: 15, minHeight: 32 },
});
