import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { Threshold } from '@/api/client';
import { useI18n } from '@/i18n';
import { Button, styles as ui } from '@/ui/components';
import { Icon } from '@/ui/icons';
import { colors, levelColors, spacing } from '@/ui/theme';

export function ThresholdField({ value, onChange }: { value: Threshold; onChange: (v: Threshold) => void }) {
  const { t } = useI18n();
  const [infoOpen, setInfoOpen] = useState(false);
  return (
    <View style={{ gap: spacing.sm }}>
      <View style={styles.titleRow}>
        <Text style={ui.bodyStrong}>{t('threshold.title')}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('threshold.infoLabel')}
          onPress={() => setInfoOpen(true)}
          hitSlop={8}
          style={({ pressed }) => [pressed && { opacity: 0.7 }]}
        >
          <Icon name="info" size={22} color={colors.primary} />
        </Pressable>
      </View>
      {([30, 50, 70] as const).map((n) => {
        const selected = value === n;
        return (
          <Pressable
            key={n}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            onPress={() => onChange(n)}
            style={({ pressed }) => [styles.option, selected && styles.optionSelected, pressed && { opacity: 0.8 }]}
          >
            <View style={[styles.radio, selected && styles.radioSelected]}>
              {selected ? <View style={styles.radioDot} /> : null}
            </View>
            <Text style={[ui.body, selected && ui.bodyStrong, { flex: 1 }]}>{t(`threshold.${n}`)}</Text>
          </Pressable>
        );
      })}
      <ThresholdInfoSheet open={infoOpen} onClose={() => setInfoOpen(false)} value={value} />
    </View>
  );
}

function ThresholdInfoSheet({ open, onClose, value }: { open: boolean; onClose: () => void; value: Threshold }) {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={t('common.close')} />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
        <View style={styles.handle} />
        <Text style={ui.title}>{t('threshold.sheetTitle')}</Text>
        <View style={styles.barWrap}>
          <View style={styles.bar}>
            <View style={[styles.segment, { flex: 30, backgroundColor: levelColors.low }]} />
            <View style={[styles.segment, { flex: 20, backgroundColor: levelColors.moderate }]} />
            <View style={[styles.segment, { flex: 20, backgroundColor: levelColors.high }]} />
            <View style={[styles.segment, { flex: 30, backgroundColor: levelColors.very_high }]} />
          </View>
          <View style={[styles.marker, { left: `${value}%` }]} />
          <View style={styles.ticks}>
            {[0, 30, 50, 70, 100].map((n) => (
              <Text key={n} style={ui.small}>
                {n}
              </Text>
            ))}
          </View>
        </View>
        <Text style={[ui.body, { textAlign: 'center' }]}>{t('threshold.chosen', { value })}</Text>
        <Text style={ui.body}>{t('threshold.sheetBody')}</Text>
        <Button label={t('common.close')} onPress={onClose} variant="secondary" />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 44 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    minHeight: 56,
  },
  optionSelected: { borderColor: colors.primary, borderWidth: 2 },
  radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: colors.muted, alignItems: 'center', justifyContent: 'center' },
  radioSelected: { borderColor: colors.primary },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
  backdrop: { flex: 1, backgroundColor: colors.backdrop },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    gap: spacing.md,
  },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: spacing.sm },
  barWrap: { gap: spacing.xs, paddingTop: spacing.sm },
  bar: { flexDirection: 'row', height: 22, borderRadius: 11, overflow: 'hidden' },
  segment: { height: '100%' },
  marker: {
    position: 'absolute',
    top: -6,
    width: 4,
    height: 34,
    borderRadius: 2,
    backgroundColor: colors.ink,
    marginLeft: -2,
  },
  ticks: { flexDirection: 'row', justifyContent: 'space-between' },
});
