import { useEffect, useMemo, useState } from 'react';
import { Modal, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { addMonths, monthGrid, monthName, weekdayNames, yearsInRange } from '@/date/calendar';
import { useI18n } from '@/i18n';
import { Button, styles as ui } from '@/ui/components';
import { Icon } from '@/ui/icons';
import { colors, spacing } from '@/ui/theme';

export function NightPicker({
  open,
  onClose,
  available,
  latest,
  selected,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  available: string[];
  latest: string;
  selected?: string;
  onSelect: (iso: string) => void;
}) {
  const { t, language } = useI18n();
  const insets = useSafeAreaInsets();
  const set = useMemo(() => new Set(available), [available]);
  const initial = selected ?? latest;
  const [view, setView] = useState({ year: Number(initial.slice(0, 4)), month: Number(initial.slice(5, 7)) - 1 });
  const [mode, setMode] = useState<'days' | 'years' | 'months'>('days');

  useEffect(() => {
    if (open) {
      const anchor = selected ?? latest;
      setView({ year: Number(anchor.slice(0, 4)), month: Number(anchor.slice(5, 7)) - 1 });
      setMode('days');
    }
  }, [open, selected, latest]);

  if (available.length === 0) return null;
  const weeks = monthGrid(view.year, view.month);
  const weekdays = weekdayNames(language);
  const years = yearsInRange(available[0], available[available.length - 1]);

  function pick(iso: string) {
    onSelect(iso);
    onClose();
  }

  function goLatest() {
    setView({ year: Number(latest.slice(0, 4)), month: Number(latest.slice(5, 7)) - 1 });
    pick(latest);
  }

  const isWeb = Platform.OS === 'web';

  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={t('common.cancel')} />
      <View style={[isWeb ? styles.centered : styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
        <View style={styles.handle} />
        <View style={styles.titleRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('common.back')}
            onPress={() => setView(addMonths(view.year, view.month, -1))}
            hitSlop={8}
            style={[styles.arrow, styles.arrowLeft]}
          >
            <Icon name="chevron-right" size={22} color={colors.primary} />
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => setMode(mode === 'days' ? 'years' : 'days')} hitSlop={8}>
            <Text style={ui.title}>
              {monthName(language, view.month)} {view.year}
            </Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('common.next')}
            onPress={() => setView(addMonths(view.year, view.month, 1))}
            hitSlop={8}
            style={styles.arrow}
          >
            <Icon name="chevron-right" size={22} color={colors.primary} />
          </Pressable>
        </View>

        {mode === 'days' && (
          <>
            <View style={styles.weekRow}>
              {weekdays.map((d, i) => (
                <Text key={i} style={styles.weekday}>
                  {d}
                </Text>
              ))}
            </View>
            {weeks.map((week, wi) => (
              <View key={wi} style={styles.weekRow}>
                {week.map((cell, ci) => {
                  if (!cell) return <View key={ci} style={styles.day} />;
                  const enabled = set.has(cell.iso);
                  const isSelected = cell.iso === selected;
                  const isLatest = cell.iso === latest;
                  return (
                    <Pressable
                      key={ci}
                      accessibilityRole="button"
                      disabled={!enabled}
                      onPress={() => pick(cell.iso)}
                      style={({ pressed }) => [
                        styles.day,
                        isSelected && styles.daySelected,
                        pressed && enabled && !isSelected && styles.dayPressed,
                      ]}
                    >
                      <Text style={[styles.dayText, !enabled && styles.dayDimmed, isSelected && styles.dayTextSelected]}>
                        {cell.day}
                      </Text>
                      {isLatest ? <View style={[styles.dot, isSelected && styles.dotSelected]} /> : <View style={styles.dotSpacer} />}
                    </Pressable>
                  );
                })}
              </View>
            ))}
          </>
        )}

        {mode === 'years' && (
          <>
            <Text style={ui.bodyStrong}>{t('calendar.selectYear')}</Text>
            <ScrollView style={styles.pickList} contentContainerStyle={styles.pickGrid}>
              {years.map((y) => (
                <Pressable
                  key={y}
                  accessibilityRole="button"
                  onPress={() => {
                    setView({ year: y, month: view.month });
                    setMode('months');
                  }}
                  style={({ pressed }) => [styles.pick, y === view.year && styles.pickSelected, pressed && { opacity: 0.7 }]}
                >
                  <Text style={[ui.body, y === view.year && styles.pickTextSelected]}>{y}</Text>
                </Pressable>
              ))}
            </ScrollView>
          </>
        )}

        {mode === 'months' && (
          <>
            <Text style={ui.bodyStrong}>{t('calendar.selectMonth')}</Text>
            <View style={styles.pickGrid}>
              {Array.from({ length: 12 }, (_, m) => (
                <Pressable
                  key={m}
                  accessibilityRole="button"
                  onPress={() => {
                    setView({ year: view.year, month: m });
                    setMode('days');
                  }}
                  style={({ pressed }) => [styles.pick, m === view.month && styles.pickSelected, pressed && { opacity: 0.7 }]}
                >
                  <Text style={[ui.body, m === view.month && styles.pickTextSelected]}>{monthName(language, m)}</Text>
                </Pressable>
              ))}
            </View>
          </>
        )}

        <View style={styles.buttons}>
          <Button label={t('calendar.latestNight')} onPress={goLatest} style={{ flex: 1 }} />
          <Button label={t('common.cancel')} variant="secondary" onPress={onClose} style={{ flex: 1 }} />
        </View>
        <View style={styles.warnRow}>
          <Icon name="info" size={16} color={colors.muted} />
          <Text style={[ui.small, { flex: 1 }]}>{t('calendar.processedWarning')}</Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: colors.backdrop },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    gap: spacing.sm,
    maxHeight: '85%',
  },
  centered: {
    alignSelf: 'center',
    width: 420,
    maxWidth: '92%',
    backgroundColor: colors.surface,
    borderRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    gap: spacing.sm,
    maxHeight: '85%',
    marginBottom: 40,
  },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: spacing.sm },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  arrow: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  arrowLeft: { transform: [{ scaleX: -1 }] },
  weekRow: { flexDirection: 'row' },
  weekday: { flex: 1, textAlign: 'center', color: colors.muted, fontSize: 12, fontWeight: '600' },
  day: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 10 },
  daySelected: { backgroundColor: colors.primary },
  dayPressed: { backgroundColor: colors.navButtonBg },
  dayText: { color: colors.text, fontSize: 15 },
  dayTextSelected: { color: colors.primaryText, fontWeight: '700' },
  dayDimmed: { color: colors.border },
  dot: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.primary, marginTop: 1 },
  dotSelected: { backgroundColor: colors.primaryText },
  dotSpacer: { height: 6 },
  pickList: { maxHeight: 260 },
  pickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  pick: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: colors.surface,
    minHeight: 44,
    justifyContent: 'center',
  },
  pickSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  pickTextSelected: { color: colors.primaryText, fontWeight: '600' },
  buttons: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
  warnRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.xs },
});
