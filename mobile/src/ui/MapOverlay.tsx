// Small controls that float over the maps: round buttons, the compact night pill, the
// "Reanalysis" chip with its explanation, a short toast and the temporary search pin.
import { useEffect, useRef, useState } from 'react';
import { Animated, Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { LatLng } from '@/geo';
import { useI18n } from '@/i18n';
import { Button, styles as ui } from './components';
import { haptic } from './feedback';
import { Icon, type IconName } from './icons';
import { currentLocation } from './location';
import { NATIVE_DRIVER } from './motion';
import { colors, radius, spacing } from './theme';

export function RoundButton({ icon, label, onPress, active }: { icon: IconName; label: string; onPress: () => void; active?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={() => {
        haptic.tap();
        onPress();
      }}
      hitSlop={6}
      style={({ pressed }) => [styles.round, active && styles.roundActive, pressed && { opacity: 0.8 }]}
    >
      <Icon name={icon} size={22} color={active ? colors.primaryText : colors.primary} />
    </Pressable>
  );
}

// Permission was denied this session: the button stays hidden until the app restarts.
let locationDenied = false;
let locationExplained = false;

// "My location": explains why before the first system prompt, then moves the camera.
export function LocateControl({ onLocated, onMessage }: { onLocated: (c: LatLng) => void; onMessage: (m: string) => void }) {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  const [hidden, setHidden] = useState(locationDenied);
  const [explaining, setExplaining] = useState(false);
  const [busy, setBusy] = useState(false);

  async function locate() {
    setExplaining(false);
    locationExplained = true;
    setBusy(true);
    const result = await currentLocation();
    setBusy(false);
    if (result.ok) {
      onLocated(result.coordinate);
      return;
    }
    if (result.reason === 'denied') {
      locationDenied = true;
      setHidden(true);
      onMessage(t('location.denied'));
    } else {
      onMessage(t('location.unavailable'));
    }
  }

  if (hidden) return null;
  return (
    <>
      <RoundButton
        icon="locate"
        label={t('map.myLocation')}
        active={busy}
        onPress={() => (locationExplained ? locate() : setExplaining(true))}
      />
      <Modal visible={explaining} transparent animationType="fade" onRequestClose={() => setExplaining(false)}>
        <Pressable style={styles.backdrop} onPress={() => setExplaining(false)} accessibilityLabel={t('common.close')} />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
          <Text style={ui.title}>{t('location.whyTitle')}</Text>
          <View style={styles.sheetRow}>
            <Icon name="locate" size={24} color={colors.primary} />
            <Text style={[ui.body, { flex: 1 }]}>{t('location.why')}</Text>
          </View>
          <Button label={t('location.allow')} icon="locate" size="large" onPress={locate} />
          <Button label={t('common.cancel')} variant="secondary" onPress={() => setExplaining(false)} />
        </View>
      </Modal>
    </>
  );
}

// Compact night selector: tapping anywhere opens the calendar sheet.
export function NightPill({ nightDate, onPress }: { nightDate?: string; onPress: () => void }) {
  const { t, formatDate, formatDateLong } = useI18n();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${nightDate ? t('common.night', { date: formatDateLong(nightDate) }) : ''}. ${t('calendar.editNight')}`}
      onPress={onPress}
      hitSlop={6}
      style={({ pressed }) => [styles.pill, pressed && { opacity: 0.85 }]}
    >
      <Icon name="calendar" size={16} color={colors.primaryText} />
      <Text style={styles.pillText}>{nightDate ? formatDate(nightDate) : '...'}</Text>
      <Icon name="edit" size={14} color={colors.primaryText} />
    </Pressable>
  );
}

// "Reanalysis" chip. The note explains that nights are processed, not live.
export function ReanalysisChip() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const insets = useSafeAreaInsets();
  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('common.reanalysis')}
        onPress={() => setOpen(true)}
        hitSlop={6}
        style={({ pressed }) => [styles.chip, pressed && { opacity: 0.85 }]}
      >
        <Icon name="info" size={14} color={colors.primary} />
        <Text style={styles.chipText}>{t('common.reanalysis')}</Text>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)} accessibilityLabel={t('common.close')} />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
          <View style={styles.sheetRow}>
            <Icon name="info" size={24} color={colors.primary} />
            <Text style={[ui.body, { flex: 1 }]}>{t('calendar.processedWarning')}</Text>
          </View>
          <Button label={t('common.close')} variant="secondary" onPress={() => setOpen(false)} />
        </View>
      </Modal>
    </>
  );
}

// Short message that fades out by itself.
export function Toast({ message, onHide }: { message: string | null; onHide: () => void }) {
  const opacity = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!message) return;
    opacity.setValue(0);
    const anim = Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 180, useNativeDriver: NATIVE_DRIVER }),
      Animated.delay(2600),
      Animated.timing(opacity, { toValue: 0, duration: 400, useNativeDriver: NATIVE_DRIVER }),
    ]);
    anim.start(({ finished }) => finished && onHide());
    return () => anim.stop();
  }, [message, opacity, onHide]);
  if (!message) return null;
  return (
    <Animated.View style={[styles.toast, { opacity }]} pointerEvents="none" accessibilityRole="alert">
      <Icon name="info" size={18} color={colors.primaryText} />
      <Text style={styles.toastText}>{message}</Text>
    </Animated.View>
  );
}

const PIN_VISIBLE_MS = 4000;

// Pin shown where a search result was selected. Fades out, then calls onDone.
export function TempPin({ onDone }: { onDone: () => void }) {
  const opacity = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    const anim = Animated.sequence([
      Animated.delay(PIN_VISIBLE_MS),
      Animated.timing(opacity, { toValue: 0, duration: 600, useNativeDriver: NATIVE_DRIVER }),
    ]);
    anim.start(({ finished }) => finished && onDone());
    return () => anim.stop();
  }, [opacity, onDone]);
  return (
    <Animated.View style={[styles.pin, { opacity }]}>
      <Icon name="pin" size={40} color={colors.danger} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  round: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: colors.mapShadow,
    shadowOpacity: 1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  roundActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    height: 36,
    paddingHorizontal: spacing.md,
    borderRadius: 18,
    backgroundColor: colors.primary,
    borderWidth: 1,
    borderColor: colors.mapHalo,
  },
  pillText: { color: colors.primaryText, fontWeight: '700', fontSize: 15 },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    height: 30,
    paddingHorizontal: 10,
    borderRadius: 15,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipText: { color: colors.primary, fontWeight: '600', fontSize: 13 },
  backdrop: { flex: 1, backgroundColor: colors.backdrop },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.xl,
    gap: spacing.lg,
  },
  sheetRow: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    alignSelf: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    maxWidth: '90%',
  },
  toastText: { color: colors.primaryText, fontSize: 15, fontWeight: '600', flexShrink: 1 },
  pin: { alignItems: 'center', justifyContent: 'center' },
});
