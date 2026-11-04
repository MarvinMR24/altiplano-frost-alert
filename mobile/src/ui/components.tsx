import { useRef, useState, type ReactNode } from 'react';
import {
  ActivityIndicator,
  Animated,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApiError, type Driver, type Level, type Reliability, type Threshold } from '@/api/client';
import { USE_MOCK } from '@/config';
import { useI18n, type TranslationKey } from '@/i18n';
import { haptic } from './feedback';
import { Icon, type IconName } from './icons';
import { Logo } from './logo';
import { Breathe, NATIVE_DRIVER, useFill } from './motion';
import { colors, LEVELS, levelColors, levelIcons, levelOnColors, percent, radius, spacing } from './theme';

export function MockBanner() {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  if (!USE_MOCK) return null;
  return (
    <View style={[styles.mockBanner, { paddingTop: insets.top + 2 }]} accessibilityRole="alert">
      <Text style={styles.mockBannerText}>{t('common.mockBanner')}</Text>
    </View>
  );
}

export function LoadingView() {
  const { t } = useI18n();
  return (
    <View style={styles.center} accessibilityRole="progressbar" accessibilityLabel={t('common.loading')}>
      <Breathe>
        <Logo size={72} />
      </Breathe>
      <Text style={styles.muted}>{t('common.loading')}</Text>
    </View>
  );
}

export function errorText(t: (key: TranslationKey) => string, error: unknown): string {
  if (error instanceof ApiError && error.status === 0) return t('common.networkError');
  return t('common.error');
}

export function ErrorView({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <View style={styles.center}>
      <Icon name="alert" size={48} color={colors.danger} />
      <Text style={[styles.errorText, { fontSize: 17 }]}>{errorText(t, error)}</Text>
      {onRetry ? <Button label={t('common.retry')} onPress={onRetry} variant="secondary" /> : null}
    </View>
  );
}

export function EmptyView({ message, icon = 'info' }: { message: string; icon?: 'info' | 'search' | 'bell' | 'layers' }) {
  return (
    <View style={styles.center}>
      <Icon name={icon} size={48} color={colors.muted} />
      <Text style={[styles.muted, { fontSize: 17 }]}>{message}</Text>
    </View>
  );
}

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'medium' | 'large';
  icon?: IconName;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

// Big, high contrast button that shrinks slightly and vibrates on touch, so a tap is
// clearly felt even with cold hands or gloves.
export function Button({ label, onPress, variant = 'primary', size = 'medium', icon, disabled, loading, style }: ButtonProps) {
  const inactive = disabled || loading;
  const scale = useRef(new Animated.Value(1)).current;
  const press = (toValue: number) =>
    Animated.spring(scale, { toValue, friction: 6, tension: 300, useNativeDriver: NATIVE_DRIVER }).start();
  const fg = variant === 'secondary' ? colors.primary : colors.primaryText;
  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityState={{ disabled: !!inactive, busy: !!loading }}
        onPress={() => {
          haptic.tap();
          onPress();
        }}
        onPressIn={() => press(0.96)}
        onPressOut={() => press(1)}
        disabled={inactive}
        hitSlop={6}
        android_ripple={{ color: variant === 'secondary' ? colors.sand : colors.navyLight }}
        style={({ pressed }) => [
          styles.button,
          size === 'large' && styles.buttonLarge,
          variant === 'secondary' && styles.buttonSecondary,
          variant === 'danger' && styles.buttonDanger,
          inactive && styles.buttonDisabled,
          pressed && !inactive && styles.buttonPressed,
        ]}
      >
        {loading ? (
          <ActivityIndicator color={fg} />
        ) : (
          <View style={styles.buttonRow}>
            {icon ? <Icon name={icon} size={22} color={fg} /> : null}
            <Text style={[styles.buttonText, size === 'large' && styles.buttonTextLarge, { color: fg }]}>{label}</Text>
          </View>
        )}
      </Pressable>
    </Animated.View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      hitSlop={4}
      style={({ pressed }) => [styles.chip, selected && styles.chipSelected, pressed && styles.pressed]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

export function ChipRow({ children }: { children: ReactNode }) {
  return <View style={styles.chipRow}>{children}</View>;
}

export function Field(
  props: TextInputProps & {
    label: string;
    icon?: 'mail' | 'lock' | 'user' | 'phone' | 'search';
    error?: string | null;
    trailing?: ReactNode;
  },
) {
  const { label, style, icon, error, trailing, onFocus, onBlur, editable = true, ...rest } = props;
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: spacing.xs }}>
      <Text style={styles.label}>{label}</Text>
      <View
        style={[
          styles.inputWrap,
          focused && styles.inputFocused,
          error ? styles.inputError : null,
          editable === false && styles.inputDisabled,
        ]}
      >
        {icon ? <Icon name={icon} size={20} color={error ? colors.danger : colors.muted} /> : null}
        <TextInput
          placeholderTextColor={colors.muted}
          style={[styles.inputInner, style]}
          editable={editable}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          {...rest}
        />
        {trailing}
      </View>
      {error ? (
        <View style={styles.fieldErrorRow}>
          <Icon name="alert" size={14} color={colors.danger} />
          <Text style={styles.fieldErrorText}>{error}</Text>
        </View>
      ) : null}
    </View>
  );
}

export function ToggleRow({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <View style={styles.toggleRow}>
      <Text style={styles.body}>{label}</Text>
      <Switch value={value} onValueChange={onChange} />
    </View>
  );
}

export function LevelBadge({ level, probability }: { level: Level; probability?: number }) {
  const { t } = useI18n();
  const label = t(`level.${level}`);
  return (
    <View style={[styles.badge, { backgroundColor: levelColors[level] }]}>
      <Icon name={levelIcons[level]} size={18} color={levelOnColors[level]} />
      <Text style={[styles.badgeText, { color: levelOnColors[level] }]}>
        {probability === undefined ? label : `${label} · ${percent(probability)}%`}
      </Text>
    </View>
  );
}

// Large risk card: icon, level word and percent, plus a four step scale that fills up to
// the level. Color, icon, word and position all say the same thing, so it reads at a
// glance and without color vision.
export function RiskMeter({ level, probability }: { level: Level; probability: number }) {
  const { t } = useI18n();
  const index = LEVELS.indexOf(level);
  return (
    <View
      style={[styles.risk, { borderColor: levelColors[level] }]}
      accessible
      accessibilityLabel={`${t('risk.meterLabel')}: ${t(`level.${level}`)}, ${percent(probability)}%`}
    >
      <View style={styles.riskTop}>
        <View style={[styles.riskIcon, { backgroundColor: levelColors[level] }]}>
          <Icon name={levelIcons[level]} size={30} color={levelOnColors[level]} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.small}>{t('risk.meterLabel')}</Text>
          <Text style={styles.riskLevel}>{t(`level.${level}`)}</Text>
        </View>
        <Text style={styles.riskPercent}>{percent(probability)}%</Text>
      </View>
      <View style={styles.riskScale}>
        {LEVELS.map((l, i) => (
          <MeterStep key={l} color={levelColors[l]} on={i <= index} delay={i * 120} current={i === index} />
        ))}
      </View>
      <View style={styles.riskLabels}>
        {LEVELS.map((l) => (
          <Text key={l} style={[styles.riskLabel, l === level && styles.riskLabelOn]} numberOfLines={1}>
            {t(`level.${l}`)}
          </Text>
        ))}
      </View>
    </View>
  );
}

function MeterStep({ color, on, delay, current }: { color: string; on: boolean; delay: number; current: boolean }) {
  const fill = useFill(on ? 1 : 0, delay);
  const width = fill.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] });
  return (
    <View style={[styles.riskStep, current && styles.riskStepCurrent]}>
      <Animated.View style={{ width, height: '100%', backgroundColor: color }} />
    </View>
  );
}

export function ReplayTag() {
  const { t } = useI18n();
  return (
    <View style={styles.replayTag} accessibilityLabel={t('history.replay')}>
      <Icon name="history" size={13} color={colors.primaryText} />
      <Text style={styles.replayText}>{t('history.replay')}</Text>
    </View>
  );
}

export function ExplanationLabel({ source }: { source?: 'muse' | 'template' }) {
  const { t } = useI18n();
  const label = source === 'muse' ? t('history.explainedMuse') : t('history.explainedTemplate');
  return (
    <View style={styles.explainRow}>
      <Icon name="info" size={14} color={colors.muted} />
      <Text style={styles.small}>{label}</Text>
    </View>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function ReanalysisNote({ nightDate }: { nightDate?: string }) {
  const { t, formatDate } = useI18n();
  return (
    <View style={{ gap: 2 }}>
      {nightDate ? <Text style={styles.nightText}>{t('common.night', { date: formatDate(nightDate) })}</Text> : null}
      <Text style={styles.small}>{t('common.reanalysisNote')}</Text>
    </View>
  );
}

// Units are encoded in the key suffix (see docs/api_contract.md).
function formatValue(key: string, value: number): string {
  if (key.endsWith('_c')) return `${value} °C`;
  if (key.endsWith('_pct')) return `${value} %`;
  if (key.endsWith('_ms')) return `${value} m/s`;
  if (key.endsWith('_hpa')) return `${value} hPa`;
  if (key.endsWith('_wm2')) return `${value} W/m²`;
  return String(value);
}

export function ConditionsList({ conditions }: { conditions: Record<string, number> }) {
  const { tOptional } = useI18n();
  return (
    <View style={{ gap: 2 }}>
      {Object.entries(conditions).map(([key, value]) => (
        <View key={key} style={styles.kvRow}>
          <Text style={styles.body}>{tOptional(`feature.${key}`, key)}</Text>
          <Text style={styles.bodyStrong}>{formatValue(key, value)}</Text>
        </View>
      ))}
    </View>
  );
}

export function DriversList({ drivers }: { drivers: Driver[] }) {
  const { t, tOptional } = useI18n();
  return (
    <View style={{ gap: 2 }}>
      {drivers.map((d) => (
        <Text key={d.feature} style={styles.body}>
          {d.effect === 'up' ? '▲' : '▼'} {tOptional(`feature.${d.feature}`, d.feature)}: {t(`driver.${d.effect}`)} ({d.weight})
        </Text>
      ))}
    </View>
  );
}

export function ReliabilityText({ reliability }: { reliability: Reliability }) {
  const { t } = useI18n();
  return (
    <Text style={styles.body}>
      {t('map.reliabilityText', {
        lo: percent(reliability.range[0]),
        hi: percent(reliability.range[1]),
        rate: percent(reliability.observed_rate),
        n: reliability.n,
      })}
    </Text>
  );
}

export const styles = StyleSheet.create({
  mockBanner: { backgroundColor: colors.mockBanner, paddingBottom: 4, alignItems: 'center' },
  mockBannerText: { color: colors.primaryText, fontWeight: '700', fontSize: 12, letterSpacing: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, padding: spacing.xl },
  muted: { color: colors.muted, textAlign: 'center', fontSize: 16 },
  small: { color: colors.muted, fontSize: 13 },
  errorText: { color: colors.danger, textAlign: 'center' },
  body: { color: colors.text, fontSize: 16, lineHeight: 23 },
  bodyStrong: { color: colors.text, fontSize: 16, fontWeight: '600' },
  label: { color: colors.muted, fontSize: 14, fontWeight: '600' },
  title: { color: colors.text, fontSize: 25, fontWeight: '700' },
  nightText: { color: colors.text, fontSize: 14, fontWeight: '600' },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '700', marginTop: spacing.md },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: colors.surface,
    color: colors.text,
    minHeight: 44,
  },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.surface,
    minHeight: 48,
  },
  inputFocused: { borderWidth: 2, borderColor: colors.primary, paddingHorizontal: spacing.md - 1 },
  inputError: { borderWidth: 2, borderColor: colors.danger, paddingHorizontal: spacing.md - 1 },
  inputDisabled: { opacity: 0.55 },
  inputInner: { flex: 1, fontSize: 16, color: colors.text, paddingVertical: 10 },
  fieldErrorRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  fieldErrorText: { color: colors.danger, fontSize: 13 },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    overflow: 'hidden',
  },
  buttonLarge: { minHeight: 58, borderRadius: 14 },
  buttonRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  buttonSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primary },
  buttonDanger: { backgroundColor: colors.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.8 },
  pressed: { opacity: 0.8 },
  buttonText: { color: colors.primaryText, fontWeight: '700', fontSize: 17 },
  buttonTextLarge: { fontSize: 18 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: colors.surface,
    minHeight: 44,
    justifyContent: 'center',
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text },
  chipTextSelected: { color: colors.primaryText, fontWeight: '600' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4, minHeight: 44 },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.md,
    paddingHorizontal: 10,
    paddingVertical: 4,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    minHeight: 34,
  },
  badgeText: { fontWeight: '700', fontSize: 15 },
  replayTag: {
    alignSelf: 'flex-start',
    borderRadius: radius.md,
    paddingHorizontal: 10,
    paddingVertical: 4,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.navyLight,
  },
  replayText: { color: colors.primaryText, fontWeight: '700', fontSize: 12 },
  explainRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.lg,
    gap: spacing.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: colors.cardShadow,
    shadowOpacity: 1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  kvRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 2 },
  risk: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 2,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  riskTop: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  riskIcon: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center' },
  riskLevel: { color: colors.text, fontSize: 26, fontWeight: '800' },
  riskPercent: { color: colors.text, fontSize: 30, fontWeight: '800' },
  riskScale: { flexDirection: 'row', gap: 4, height: 14 },
  riskStep: { flex: 1, borderRadius: 7, overflow: 'hidden', backgroundColor: colors.border },
  riskStepCurrent: { borderWidth: 2, borderColor: colors.text },
  riskLabels: { flexDirection: 'row', gap: 4 },
  riskLabel: { flex: 1, textAlign: 'center', fontSize: 12, color: colors.muted },
  riskLabelOn: { color: colors.text, fontWeight: '800' },
});
