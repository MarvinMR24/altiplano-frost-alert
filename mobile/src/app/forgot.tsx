import { router } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

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
  StepSlide,
  useCountdown,
} from '@/ui/auth';
import { Button, Field, styles as ui } from '@/ui/components';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotScreen() {
  const { t } = useI18n();
  const { forgotPassword, resetPassword } = useAuth();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const countdown = useCountdown(60, step);

  async function sendCode() {
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setFieldError(t('auth.invalidEmail'));
      return;
    }
    setFieldError(null);
    setBusy(true);
    setError(null);
    try {
      await forgotPassword(value);
      setEmail(value);
      setStep(2);
    } catch (err) {
      setError(t('common.networkError'));
    } finally {
      setBusy(false);
    }
  }

  function nextFromCode() {
    if (!/^\d{6}$/.test(code)) {
      setError(t('auth.codeFormat'));
      return;
    }
    setError(null);
    setStep(3);
  }

  async function submitNewPassword() {
    const problem = passwordProblem(password);
    if (problem) {
      setFieldError(t(problem));
      return;
    }
    if (confirm !== password) {
      setFieldError(t('signup.passwordMismatch'));
      return;
    }
    setFieldError(null);
    setBusy(true);
    setError(null);
    try {
      // On success the auth guard swaps this screen for onboarding or the tabs.
      await resetPassword(email, code, password);
    } catch (err) {
      const isCodeError = err instanceof ApiError && err.status >= 400 && err.status < 500;
      setError(isCodeError ? t('auth.invalidCode') : t('common.networkError'));
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await forgotPassword(email);
      countdown.restart();
    } catch (err) {
      setError(t('common.networkError'));
    }
  }

  return (
    <AuthShell
      title={t('forgot.title')}
      subtitle={step === 1 ? t('forgot.emailBody') : step === 2 ? t('forgot.codeBody', { email }) : t('forgot.newPasswordBody')}
      onBack={() => (step === 1 ? router.back() : setStep(step - 1))}
    >
      <StepSlide stepKey={step}>
        {step === 1 && (
          <AuthCard>
            <Field
              label={t('auth.emailLabel')}
              icon="mail"
              placeholder={t('auth.emailPlaceholder')}
              value={email}
              onChangeText={setEmail}
              error={fieldError}
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
              autoFocus
              returnKeyType="send"
            />
            <InlineError message={error} />
            <Button label={t('auth.sendCode')} size="large" onPress={sendCode} loading={busy} />
          </AuthCard>
        )}
        {step === 2 && (
          <AuthCard>
            <CodeInput value={code} onChange={setCode} />
            <InlineError message={error} />
            <Button label={t('common.next')} size="large" onPress={nextFromCode} />
            {countdown.left > 0 ? (
              <Text style={[ui.small, { textAlign: 'center' }]}>{t('auth.resendIn', { s: countdown.left })}</Text>
            ) : (
              <Button label={t('auth.resend')} variant="secondary" onPress={resend} />
            )}
            {USE_MOCK ? <Text style={ui.small}>{t('auth.mockHint')}</Text> : null}
          </AuthCard>
        )}
        {step === 3 && (
          <AuthCard>
            <PasswordField
              label={t('password.new')}
              value={password}
              onChangeText={setPassword}
              error={fieldError}
              autoFocus
            />
            <PasswordMeter password={password} />
            <PasswordField label={t('password.confirm')} value={confirm} onChangeText={setConfirm} />
            <InlineError message={error} />
            <Button label={t('common.save')} size="large" onPress={submitNewPassword} loading={busy} />
          </AuthCard>
        )}
      </StepSlide>
    </AuthShell>
  );
}
