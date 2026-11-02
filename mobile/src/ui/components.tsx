import type { ReactNode } from 'react';
import {
  ActivityIndicator,
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
import { colors, levelColors, percent, spacing } from './theme';

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
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} />
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
      <Text style={styles.errorText}>{errorText(t, error)}</Text>
      {onRetry ? <Button label={t('common.retry')} onPress={onRetry} variant="secondary" /> : null}
    </View>
  );
}

export function EmptyView({ message }: { message: string }) {
  return (
    <View style={styles.center}>
      <Text style={styles.muted}>{message}</Text>
    </View>
  );
}

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

export function Button({ label, onPress, variant = 'primary', disabled, loading, style }: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        variant === 'secondary' && styles.buttonSecondary,
        variant === 'danger' && styles.buttonDanger,
        inactive && styles.buttonDisabled,
        pressed && !inactive && styles.buttonPressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'secondary' ? colors.primary : '#fff'} />
      ) : (
        <Text style={[styles.buttonText, variant === 'secondary' && styles.buttonTextSecondary]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, selected && styles.chipSelected]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

export function ChipRow({ children }: { children: ReactNode }) {
  return <View style={styles.chipRow}>{children}</View>;
}

export function Field(props: TextInputProps & { label: string }) {
  const { label, style, ...rest } = props;
  return (
    <View style={{ gap: spacing.xs }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput placeholderTextColor={colors.muted} style={[styles.input, style]} {...rest} />
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

export const THRESHOLDS: Threshold[] = [30, 50, 70];

export function ThresholdPicker({ value, onChange }: { value: Threshold; onChange: (v: Threshold) => void }) {
  const { t } = useI18n();
  return (
    <ChipRow>
      {THRESHOLDS.map((n) => (
        <Chip key={n} label={t('common.percent', { value: n })} selected={value === n} onPress={() => onChange(n)} />
      ))}
    </ChipRow>
  );
}

export function LevelBadge({ level, probability }: { level: Level; probability?: number }) {
  const { t } = useI18n();
  const label = t(`level.${level}`);
  return (
    <View style={[styles.badge, { backgroundColor: levelColors[level] }]}>
      <Text style={styles.badgeText}>
        {probability === undefined ? label : `${label} · ${percent(probability)}%`}
      </Text>
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
  mockBannerText: { color: '#fff', fontWeight: '700', fontSize: 12, letterSpacing: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, padding: spacing.xl },
  muted: { color: colors.muted, textAlign: 'center' },
  small: { color: colors.muted, fontSize: 12 },
  errorText: { color: colors.danger, textAlign: 'center' },
  body: { color: colors.text, fontSize: 15 },
  bodyStrong: { color: colors.text, fontSize: 15, fontWeight: '600' },
  label: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  title: { color: colors.text, fontSize: 24, fontWeight: '700' },
  nightText: { color: colors.text, fontSize: 14, fontWeight: '600' },
  sectionTitle: { color: colors.text, fontSize: 16, fontWeight: '700', marginTop: spacing.md },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: colors.surface,
    color: colors.text,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 46,
  },
  buttonSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primary },
  buttonDanger: { backgroundColor: colors.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.8 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  buttonTextSecondary: { color: colors.primary },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: colors.surface,
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text },
  chipTextSelected: { color: '#fff', fontWeight: '600' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4 },
  badge: { alignSelf: 'flex-start', borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText: { color: '#1C1C1E', fontWeight: '700', fontSize: 13 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.lg,
    gap: spacing.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  kvRow: { flexDirection: 'row', justifyContent: 'space-between' },
});
