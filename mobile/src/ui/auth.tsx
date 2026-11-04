import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  Animated,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputInstance,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { LANGUAGES, useI18n } from '@/i18n';
import { socialComingSoon } from '@/auth/providers';
import { Field, styles as ui } from '@/ui/components';
import { haptic } from '@/ui/feedback';
import { Icon } from '@/ui/icons';
import { Logo } from '@/ui/logo';
import { NATIVE_DRIVER, useReduceMotion, useShake } from '@/ui/motion';
import { colors, spacing } from '@/ui/theme';
import type { TranslationKey } from '@/i18n';

export { useReduceMotion };

// Slides content in from the right when stepKey changes. Skips motion when reduced.
export function StepSlide({ stepKey, children }: { stepKey: string | number; children: ReactNode }) {
  const reduceMotion = useReduceMotion();
  const slide = useRef(new Animated.Value(0)).current;
  const fade = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) {
      slide.setValue(0);
      fade.setValue(1);
      return;
    }
    slide.setValue(28);
    fade.setValue(0);
    Animated.parallel([
      Animated.timing(slide, { toValue: 0, duration: 220, useNativeDriver: NATIVE_DRIVER }),
      Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: NATIVE_DRIVER }),
    ]).start();
  }, [stepKey, reduceMotion, slide, fade]);
  return <Animated.View style={{ opacity: fade, transform: [{ translateX: slide }] }}>{children}</Animated.View>;
}

export function StepProgress({ step, total }: { step: number; total: number }) {
  const { t } = useI18n();
  return (
    <View style={authStyles.progress}>
      <Text style={ui.small}>{t('onboarding.step', { n: step, total })}</Text>
      <View style={authStyles.dots}>
        {Array.from({ length: total }, (_, i) => (
          <ProgressDot key={i} done={i < step} />
        ))}
      </View>
    </View>
  );
}

function ProgressDot({ done }: { done: boolean }) {
  const fill = useRef(new Animated.Value(done ? 1 : 0)).current;
  const reduceMotion = useReduceMotion();
  useEffect(() => {
    if (reduceMotion) fill.setValue(done ? 1 : 0);
    else Animated.timing(fill, { toValue: done ? 1 : 0, duration: 350, useNativeDriver: false }).start();
  }, [done, reduceMotion, fill]);
  const width = fill.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] });
  return (
    <View style={authStyles.dot}>
      <Animated.View style={[authStyles.dotDone, { width }]} />
    </View>
  );
}

export function AuthShell({
  title,
  subtitle,
  onBack,
  backLabel,
  children,
}: {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  backLabel?: string;
  children: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={authStyles.shell} keyboardShouldPersistTaps="handled">
          {onBack ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={backLabel ?? t('common.back')}
              onPress={onBack}
              hitSlop={8}
              style={({ pressed }) => [authStyles.backRow, pressed && { opacity: 0.7 }]}
            >
              <Icon name="arrow-left" size={20} color={colors.primary} />
              <Text style={authStyles.backText}>{backLabel ?? t('common.back')}</Text>
            </Pressable>
          ) : null}
          <View style={{ alignItems: 'center', gap: spacing.sm }}>
            <Logo size={72} />
            <Text style={ui.title}>{title}</Text>
            {subtitle ? <Text style={[ui.muted, { textAlign: 'center' }]}>{subtitle}</Text> : null}
          </View>
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export function PasswordField({
  label,
  value,
  onChangeText,
  error,
  placeholder,
  autoFocus,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  error?: string | null;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const { t } = useI18n();
  const [shown, setShown] = useState(false);
  return (
    <Field
      label={label}
      icon="lock"
      value={value}
      onChangeText={onChangeText}
      error={error}
      placeholder={placeholder}
      autoFocus={autoFocus}
      secureTextEntry={!shown}
      autoCapitalize="none"
      autoCorrect={false}
      textContentType="password"
      trailing={
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={shown ? t('common.hidePassword') : t('common.showPassword')}
          onPress={() => setShown(!shown)}
          hitSlop={8}
          style={({ pressed }) => [pressed && { opacity: 0.7 }]}
        >
          <Icon name={shown ? 'eye-off' : 'eye'} size={22} color={colors.muted} />
        </Pressable>
      }
    />
  );
}

export type PasswordStrength = 'weak' | 'fair' | 'strong';

export function passwordRules(password: string): { length: boolean; letter: boolean; number: boolean } {
  return {
    length: password.length >= 8,
    letter: /[A-Za-z]/.test(password),
    number: /\d/.test(password),
  };
}

export function passwordStrength(password: string): PasswordStrength {
  const rules = passwordRules(password);
  const passed = [rules.length, rules.letter, rules.number].filter(Boolean).length;
  if (passed < 3) return 'weak';
  return password.length >= 12 ? 'strong' : 'fair';
}

// Message for the first rule the password breaks, or null when it passes.
export function passwordProblem(password: string): TranslationKey | null {
  const rules = passwordRules(password);
  if (!rules.length) return 'signup.ruleLength';
  if (!rules.letter) return 'signup.ruleLetter';
  if (!rules.number) return 'signup.ruleNumber';
  return null;
}

// The checklist is always visible, so people see the rules before they type.
export function PasswordMeter({ password }: { password: string }) {
  const { t } = useI18n();
  const rules = passwordRules(password);
  const strength = passwordStrength(password);
  const strengthKey = strength === 'weak' ? 'signup.strengthWeak' : strength === 'fair' ? 'signup.strengthFair' : 'signup.strengthStrong';
  const rows: { ok: boolean; label: string }[] = [
    { ok: rules.length, label: t('signup.ruleLength') },
    { ok: rules.letter, label: t('signup.ruleLetter') },
    { ok: rules.number, label: t('signup.ruleNumber') },
  ];
  return (
    <View style={{ gap: spacing.xs }}>
      {password ? (
        <View style={authStyles.meterRow}>
          {(['weak', 'fair', 'strong'] as const).map((level, i) => {
            const order = { weak: 0, fair: 1, strong: 2 };
            const active = order[strength] >= i;
            return <View key={level} style={[authStyles.meterBar, active && authStyles.meterBarOn]} />;
          })}
          <Text style={ui.small}>{t(strengthKey)}</Text>
        </View>
      ) : null}
      {rows.map((row) => (
        <View key={row.label} style={authStyles.ruleRow}>
          <Icon name={row.ok ? 'check-circle' : 'check'} size={18} color={row.ok ? colors.teal : colors.muted} />
          <Text style={[ui.small, { fontSize: 14 }, row.ok && { color: colors.teal, fontWeight: '600' }]}>{row.label}</Text>
        </View>
      ))}
    </View>
  );
}

// Six digit code input: one hidden field drives six boxes, so paste and auto
// advance work on every platform.
export function CodeInput({ value, onChange, onComplete }: { value: string; onChange: (v: string) => void; onComplete?: (code: string) => void }) {
  const input = useRef<TextInputInstance | null>(null);
  function handle(text: string) {
    const digits = text.replace(/\D/g, '').slice(0, 6);
    onChange(digits);
    if (digits.length === 6) onComplete?.(digits);
  }
  return (
    <Pressable onPress={() => input.current?.focus()} accessibilityRole="button">
      <View style={authStyles.codeRow}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <View
            key={i}
            style={[authStyles.codeBox, value[i] ? authStyles.codeBoxFilled : null, value.length === i && authStyles.codeBoxActive]}
          >
            <Text style={authStyles.codeDigit}>{value[i] ?? ''}</Text>
          </View>
        ))}
      </View>
      <TextInput
        ref={input}
        value={value}
        onChangeText={handle}
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="one-time-code"
        maxLength={6}
        autoFocus
        style={authStyles.codeHidden}
      />
    </Pressable>
  );
}

export function useCountdown(seconds: number, activeKey: unknown): { left: number; restart: () => void } {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    setLeft(seconds);
    const timer = setInterval(() => setLeft((v) => (v > 0 ? v - 1 : 0)), 1000);
    return () => clearInterval(timer);
  }, [seconds, activeKey]);
  return { left, restart: () => setLeft(seconds) };
}

export function SocialButtons() {
  const { t } = useI18n();
  const [notice, setNotice] = useState(false);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(false), 3000);
    return () => clearTimeout(timer);
  }, [notice]);
  function comingSoon() {
    socialComingSoon();
    setNotice(true);
  }
  return (
    <View style={{ gap: spacing.sm }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('welcome.google')}
        onPress={comingSoon}
        style={({ pressed }) => [authStyles.social, authStyles.socialGoogle, pressed && { opacity: 0.8 }]}
      >
        <Ionicons name="logo-google" size={20} color={colors.text} />
        <Text style={authStyles.socialGoogleText}>{t('welcome.google')}</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('welcome.apple')}
        onPress={comingSoon}
        style={({ pressed }) => [authStyles.social, authStyles.socialApple, pressed && { opacity: 0.8 }]}
      >
        <Ionicons name="logo-apple" size={20} color={colors.white} />
        <Text style={authStyles.socialAppleText}>{t('welcome.apple')}</Text>
      </Pressable>
      {notice ? <Text style={[ui.small, { textAlign: 'center' }]}>{t('welcome.comingSoon')}</Text> : null}
    </View>
  );
}

export function OrDivider() {
  const { t } = useI18n();
  return (
    <View style={authStyles.orRow}>
      <View style={authStyles.orLine} />
      <Text style={ui.small}>{t('common.or')}</Text>
      <View style={authStyles.orLine} />
    </View>
  );
}

export function LanguageChips() {
  const { t, language, setLanguage } = useI18n();
  return (
    <View style={{ gap: spacing.xs }}>
      <View style={authStyles.langRow}>
        <Icon name="globe" size={18} color={colors.muted} />
        {LANGUAGES.map((l) => {
          const selected = language === l.id;
          return (
            <Pressable
              key={l.id}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => setLanguage(l.id)}
              hitSlop={4}
              style={({ pressed }) => [
                authStyles.langChip,
                selected && authStyles.langChipSelected,
                pressed && { opacity: 0.8 },
              ]}
            >
              {selected ? <Icon name="check" size={14} color={selected ? colors.primaryText : colors.text} /> : null}
              <Text style={[authStyles.langText, selected && authStyles.langTextSelected]}>{t(l.labelKey)}</Text>
            </Pressable>
          );
        })}
      </View>
      {language === 'ay' || language === 'qu' ? (
        <Text style={[ui.small, { textAlign: 'center' }]}>{t('language.partialNote')}</Text>
      ) : null}
    </View>
  );
}

// Error line that shakes and vibrates when a new message appears.
export function InlineError({ message }: { message: string | null }) {
  const offset = useShake(message);
  useEffect(() => {
    if (message) haptic.warning();
  }, [message]);
  if (!message) return null;
  return (
    <Animated.View style={[authStyles.inlineError, { transform: [{ translateX: offset }] }]} accessibilityRole="alert">
      <Icon name="alert" size={20} color={colors.danger} />
      <Text style={[ui.body, { color: colors.danger, flex: 1, fontWeight: '600' }]}>{message}</Text>
    </Animated.View>
  );
}

export function AuthCard({ children }: { children: ReactNode }) {
  return <View style={authStyles.card}>{children}</View>;
}

const authStyles = StyleSheet.create({
  shell: { flexGrow: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: 'center' },
  backRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs, alignSelf: 'flex-start', minHeight: 44 },
  backText: { color: colors.primary, fontWeight: '600', fontSize: 16 },
  progress: { gap: spacing.xs },
  dots: { flexDirection: 'row', gap: spacing.xs },
  dot: { flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden' },
  dotDone: { height: '100%', backgroundColor: colors.primary },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    gap: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  meterRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  meterBar: { flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.border },
  meterBarOn: { backgroundColor: colors.teal },
  ruleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  codeRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.sm },
  codeBox: {
    flex: 1,
    aspectRatio: 0.85,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  codeBoxActive: { borderWidth: 3, borderColor: colors.primary },
  codeBoxFilled: { backgroundColor: colors.beige, borderColor: colors.primary },
  codeDigit: { fontSize: 30, fontWeight: '700', color: colors.text },
  codeHidden: { position: 'absolute', width: 1, height: 1, opacity: 0 },
  social: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    minHeight: 52,
    borderRadius: 14,
  },
  socialGoogle: { backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  socialGoogleText: { color: colors.text, fontWeight: '600', fontSize: 16 },
  socialApple: { backgroundColor: colors.black },
  socialAppleText: { color: colors.white, fontWeight: '600', fontSize: 16 },
  orRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  orLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: colors.border },
  langRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  langChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.surface,
    minHeight: 44,
  },
  langChipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  langText: { color: colors.text },
  langTextSelected: { color: colors.primaryText, fontWeight: '600' },
  inlineError: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.xs },
});
