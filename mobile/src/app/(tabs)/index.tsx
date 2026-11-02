import { useCallback, useMemo, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, Polygon, type Region } from 'react-native-maps';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type Cell } from '@/api/client';
import { fromPolygon } from '@/geo';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import {
  Button,
  ConditionsList,
  DriversList,
  ErrorView,
  LevelBadge,
  LoadingView,
  ReanalysisNote,
  ReliabilityText,
  SectionTitle,
  styles as ui,
} from '@/ui/components';
import { colors, LEVELS, levelColors, percent, spacing } from '@/ui/theme';

const INITIAL_REGION: Region = { latitude: -17.4, longitude: -68.0, latitudeDelta: 2.6, longitudeDelta: 2.6 };

export default function MapScreen() {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  const [night, setNight] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<Cell | null>(null);

  const base = useAsync(() => Promise.all([api.getCoverage(), api.getNights()]), []);
  const aois = useAsync(() => api.listAois(), [], { refetchOnFocus: true });
  const map = useAsync(() => api.getMap(night), [night]);

  const coverage = base.data?.[0];
  const nights = base.data?.[1];
  const nightDate = night ?? map.data?.night_date ?? nights?.latest;
  // Never show cells from another night while a new one loads or after an error.
  const cells = map.data && !map.error && (!night || map.data.night_date === night) ? map.data.cells : [];
  const index = nights && nightDate ? nights.available.indexOf(nightDate) : -1;

  const go = useCallback(
    (delta: number) => {
      if (!nights || index < 0) return;
      const next = nights.available[index + delta];
      if (next) setNight(next);
    },
    [nights, index],
  );

  const coveragePolygons = useMemo(
    () =>
      coverage?.features.map((f) => (
        <Polygon
          key={`cov-${f.properties.point_id}`}
          coordinates={fromPolygon(f.geometry)}
          fillColor={colors.coverageFill}
          strokeColor={colors.coverageStroke}
          strokeWidth={1}
          tappable={false}
        />
      )),
    [coverage],
  );

  if (base.loading && !base.data) return <LoadingView />;
  if (base.error) return <ErrorView error={base.error} onRetry={base.reload} />;

  return (
    <View style={{ flex: 1 }}>
      <MapView style={StyleSheet.absoluteFill} initialRegion={INITIAL_REGION}>
        {coveragePolygons}
        {aois.data?.map((a) => (
          <Polygon
            key={`aoi-${a.id}`}
            coordinates={fromPolygon(a.polygon)}
            fillColor={colors.aoiFill}
            strokeColor={colors.aoiStroke}
            strokeWidth={2}
            tappable={false}
          />
        ))}
        {cells.map((c) => (
          <Marker
            key={`${nightDate}-${c.point_id}`}
            coordinate={{ latitude: c.lat, longitude: c.lon }}
            onPress={() => setSelected(c)}
            anchor={{ x: 0.5, y: 0.5 }}
          >
            <View style={[styles.cellDot, { backgroundColor: levelColors[c.level] }]}>
              <Text style={styles.cellText}>{percent(c.probability)}%</Text>
            </View>
          </Marker>
        ))}
      </MapView>

      <View style={[styles.topBar, { top: insets.top + spacing.sm }]}>
        <View style={styles.nightRow}>
          <NavButton label={`‹ ${t('map.previous')}`} disabled={index <= 0} onPress={() => go(-1)} />
          <View style={{ flex: 1, alignItems: 'center' }}>
            {nightDate ? <ReanalysisNote nightDate={nightDate} /> : null}
          </View>
          <NavButton
            label={`${t('map.next')} ›`}
            disabled={!nights || index < 0 || index >= nights.available.length - 1}
            onPress={() => go(1)}
          />
        </View>
        <View style={styles.statusRow}>
          {map.loading ? <Text style={ui.small}>{t('common.loading')}</Text> : null}
          {map.error ? (
            <Pressable onPress={map.reload}>
              <Text style={ui.errorText}>{t('map.noData')} {t('common.retry')}</Text>
            </Pressable>
          ) : null}
          {nights && nightDate !== nights.latest ? (
            <NavButton label={t('map.latest')} onPress={() => setNight(nights.latest)} />
          ) : null}
        </View>
      </View>

      <Legend />

      <CellSheet cell={selected} nightDate={nightDate} onClose={() => setSelected(null)} />
    </View>
  );
}

function NavButton({ label, onPress, disabled }: { label: string; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={[styles.navButton, disabled && { opacity: 0.35 }]}
    >
      <Text style={styles.navText}>{label}</Text>
    </Pressable>
  );
}

function Legend() {
  const { t } = useI18n();
  return (
    <View style={styles.legend}>
      <Text style={ui.label}>{t('map.legend')}</Text>
      {LEVELS.map((l) => (
        <View key={l} style={styles.legendRow}>
          <View style={[styles.swatch, { backgroundColor: levelColors[l], borderRadius: 7 }]} />
          <Text style={styles.legendText}>{t(`level.${l}`)}</Text>
        </View>
      ))}
      <View style={styles.legendRow}>
        <View style={[styles.swatch, { backgroundColor: colors.coverageFill, borderColor: colors.coverageStroke }]} />
        <Text style={styles.legendText}>{t('map.coverage')}</Text>
      </View>
      <View style={styles.legendRow}>
        <View style={[styles.swatch, { backgroundColor: colors.aoiFill, borderColor: colors.aoiStroke }]} />
        <Text style={styles.legendText}>{t('map.yourZones')}</Text>
      </View>
    </View>
  );
}

function CellSheet({ cell, nightDate, onClose }: { cell: Cell | null; nightDate?: string; onClose: () => void }) {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={!!cell} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={t('common.close')} />
      {cell ? (
        <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
          <View style={styles.handle} />
          <ScrollView contentContainerStyle={{ gap: spacing.sm }}>
            <Text style={ui.title}>{cell.name}</Text>
            <Text style={ui.small}>{t('map.elevation', { m: Math.round(cell.elevation_m) })}</Text>
            <ReanalysisNote nightDate={nightDate} />
            <SectionTitle>{t('map.probability')}</SectionTitle>
            <LevelBadge level={cell.level} probability={cell.probability} />
            <SectionTitle>{t('map.drivers')}</SectionTitle>
            <DriversList drivers={cell.top_drivers} />
            <SectionTitle>{t('map.conditions')}</SectionTitle>
            <ConditionsList conditions={cell.conditions_1800} />
            <SectionTitle>{t('map.reliability')}</SectionTitle>
            <ReliabilityText reliability={cell.historical_reliability} />
            <SectionTitle>{t('map.whatHappened')}</SectionTitle>
            <Text style={ui.body}>
              {cell.observed
                ? t(cell.observed.frost ? 'map.frostObserved' : 'map.noFrostObserved', { t: cell.observed.tmin_c })
                : t('map.notYetKnown')}
            </Text>
            <Button label={t('common.close')} onPress={onClose} variant="secondary" style={{ marginTop: spacing.md }} />
          </ScrollView>
        </View>
      ) : null}
    </Modal>
  );
}

const styles = StyleSheet.create({
  cellDot: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },
  cellText: { fontWeight: '800', color: '#1C1C1E', fontSize: 13 },
  topBar: {
    position: 'absolute',
    left: spacing.md,
    right: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.95)',
    borderRadius: 12,
    padding: spacing.sm,
    gap: spacing.xs,
  },
  nightRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  statusRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: spacing.md },
  navButton: { paddingHorizontal: spacing.sm, paddingVertical: 6, borderRadius: 8, backgroundColor: '#EEF2F7' },
  navText: { color: colors.primary, fontWeight: '600', fontSize: 13 },
  legend: {
    position: 'absolute',
    left: spacing.md,
    bottom: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.95)',
    borderRadius: 10,
    padding: spacing.sm,
    gap: 3,
  },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendText: { fontSize: 12, color: colors.text },
  swatch: { width: 14, height: 14, borderWidth: 1, borderColor: '#fff' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.25)' },
  sheet: {
    maxHeight: '75%',
    backgroundColor: colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
  },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: spacing.sm },
});
