import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, type MapViewHandle, type Region } from '@/ui/maps';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type Cell, type Level } from '@/api/client';
import { fromPolygon, type LatLng } from '@/geo';
import type { PlaceResult } from '@/geo/search';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import {
  Button,
  ConditionsList,
  DriversList,
  EmptyView,
  ErrorView,
  ExplanationLabel,
  LoadingView,
  ReanalysisNote,
  ReliabilityText,
  ReplayTag,
  RiskMeter,
  SectionTitle,
  styles as ui,
} from '@/ui/components';
import { haptic } from '@/ui/feedback';
import { Icon } from '@/ui/icons';
import { FadeIn, NATIVE_DRIVER, PulseRing } from '@/ui/motion';
import { SpeakButton } from '@/ui/SpeakButton';
import { MuseExplanation } from '@/ui/MuseExplanation';
import { TechnicalInfo } from '@/ui/TechnicalInfo';
import { LocateControl, NightPill, ReanalysisChip, RoundButton, TempPin, Toast } from '@/ui/MapOverlay';
import { nativeMapType, useMapLayer } from '@/ui/mapLayer';
import { MapSearch } from '@/ui/MapSearch';
import { CoverageLabels, HaloPolygon } from '@/ui/mapShapes';
import { NightPicker } from '@/ui/NightPicker';
import { colors, LEVELS, levelColors, levelIcons, levelOnColors, percent, spacing } from '@/ui/theme';

// Fits all 8 cells plus their 30 km circles, including Charana and Huanuni.
const FULL_REGION: Region = { latitude: -17.4, longitude: -68.1, latitudeDelta: 2.7, longitudeDelta: 3.5 };

// Neighborhood view after a search or "My location".
const PLACE_DELTA = 0.05;

function cellRegion(cell: Cell): Region {
  return { latitude: cell.lat, longitude: cell.lon, latitudeDelta: 0.7, longitudeDelta: 0.7 };
}

const PULSING: Level[] = ['high', 'very_high'];

const CellMarker = memo(function CellMarker({ cell, onPress }: { cell: Cell; onPress: (c: Cell) => void }) {
  const handlePress = useCallback(() => onPress(cell), [onPress, cell]);
  const pulsing = PULSING.includes(cell.level);
  return (
    <Marker
      coordinate={{ latitude: cell.lat, longitude: cell.lon }}
      onPress={handlePress}
      anchor={{ x: 0.5, y: 0.5 }}
      // Only the few high risk markers redraw, to keep their pulse running.
      tracksViewChanges={pulsing}
    >
      <View style={styles.cellWrap}>
        <PulseRing size={52} color={levelColors[cell.level]} active={pulsing} />
        <View style={[styles.cellDot, { backgroundColor: levelColors[cell.level] }]}>
          <Icon name={levelIcons[cell.level]} size={14} color={levelOnColors[cell.level]} />
          <Text style={[styles.cellText, { color: levelOnColors[cell.level] }]}>{percent(cell.probability)}%</Text>
        </View>
      </View>
    </Marker>
  );
});

export default function MapScreen() {
  const { t } = useI18n();
  const insets = useSafeAreaInsets();
  const { layer, toggle: toggleLayer } = useMapLayer();
  const [pin, setPin] = useState<LatLng | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const hideToast = useCallback(() => setToast(null), []);
  const hidePin = useCallback(() => setPin(null), []);
  const mapRef = useRef<MapViewHandle | null>(null);
  const [night, setNight] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<Cell | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const flash = useRef(new Animated.Value(0)).current;

  const base = useAsync(() => Promise.all([api.getCoverage(), api.getNights()]), []);
  const aois = useAsync(() => api.listAois(), [], { refetchOnFocus: true });
  const map = useAsync(() => api.getMap(night), [night]);

  const coverage = base.data?.[0];
  const nights = base.data?.[1];
  const nightDate = night ?? map.data?.night_date ?? nights?.latest;
  const cells = map.data && !map.error && (!night || map.data.night_date === night) ? map.data.cells : [];

  // Brief flash so the marker levels fade between nights.
  useEffect(() => {
    flash.setValue(0.25);
    Animated.timing(flash, { toValue: 0, duration: 300, useNativeDriver: NATIVE_DRIVER }).start();
  }, [nightDate, flash]);

  const pickNight = useCallback((iso: string) => {
    setSelected(null);
    setNight(iso);
  }, []);

  const selectCell = useCallback((cell: Cell) => {
    haptic.tap();
    setSelected(cell);
    mapRef.current?.animateToRegion(cellRegion(cell), 500);
  }, []);

  const goTo = useCallback((point: LatLng) => {
    setPin(point);
    mapRef.current?.animateToRegion({ ...point, latitudeDelta: PLACE_DELTA, longitudeDelta: PLACE_DELTA }, 700);
  }, []);

  const selectPlace = useCallback(
    (place: PlaceResult) => {
      if (!place.inCoverage) setToast(t('search.noFrostData'));
      goTo({ latitude: place.latitude, longitude: place.longitude });
    },
    [goTo, t],
  );

  const closeSheet = useCallback(() => {
    setSelected(null);
    mapRef.current?.animateToRegion(FULL_REGION, 500);
  }, []);

  const coveragePolygons = useMemo(
    () =>
      coverage?.features.map((f) => (
        <HaloPolygon
          key={`cov-${f.properties.point_id}`}
          coordinates={fromPolygon(f.geometry)}
          fillColor={colors.coverageFill}
          strokeColor={colors.coverageStroke}
          strokeWidth={1.5}
        />
      )),
    [coverage],
  );

  const zonePolygons = useMemo(
    () =>
      aois.data?.map((a) => (
        <HaloPolygon
          key={`aoi-${a.id}`}
          coordinates={fromPolygon(a.polygon)}
          fillColor={colors.aoiFill}
          strokeColor={colors.aoiStroke}
          strokeWidth={2.5}
        />
      )),
    [aois.data],
  );

  const cellMarkers = useMemo(
    () => cells.map((c) => <CellMarker key={`${nightDate}-${c.point_id}`} cell={c} onPress={selectCell} />),
    [cells, nightDate, selectCell],
  );

  if (base.loading && !base.data) return <LoadingView />;
  if (base.error) return <ErrorView error={base.error} onRetry={base.reload} />;

  const showEmpty = !map.loading && !map.error && cells.length === 0;

  return (
    <View style={{ flex: 1 }}>
      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFill}
        initialRegion={FULL_REGION}
        mapType={nativeMapType(layer)}
        showsPointsOfInterests={false}
        showsCompass={false}
        rotateEnabled={false}
        pitchEnabled={false}
        toolbarEnabled={false}
        moveOnMarkerPress={false}
      >
        {coveragePolygons}
        {zonePolygons}
        {coverage ? <CoverageLabels coverage={coverage} /> : null}
        {cellMarkers}
        {pin ? (
          <Marker coordinate={pin} anchor={{ x: 0.5, y: 1 }} tracksViewChanges>
            <TempPin onDone={hidePin} />
          </Marker>
        ) : null}
      </MapView>

      <Animated.View style={[StyleSheet.absoluteFill, { opacity: flash, backgroundColor: colors.beige }]} pointerEvents="none" />

      <View style={[styles.top, { top: insets.top + spacing.sm }]} pointerEvents="box-none">
        <MapSearch coverage={coverage} allowOutside onSelect={selectPlace} />
        <View style={styles.controlsRow} pointerEvents="box-none">
          <View style={styles.leftControls}>
            <NightPill nightDate={nightDate} onPress={() => setPickerOpen(true)} />
            <ReanalysisChip />
          </View>
          <View style={styles.rightControls}>
            <RoundButton
              icon="layers"
              label={t('map.switchLayer', { layer: t(layer === 'satellite' ? 'map.layerMap' : 'map.layerSatellite') })}
              onPress={toggleLayer}
            />
            <LocateControl onLocated={goTo} onMessage={setToast} />
          </View>
        </View>
        {map.loading || map.error || showEmpty ? (
          <View style={styles.status}>
            {map.loading ? <Text style={ui.small}>{t('common.loading')}</Text> : null}
            {map.error ? (
              <Pressable onPress={map.reload} hitSlop={8}>
                <Text style={ui.errorText}>
                  {t('map.noData')} {t('common.retry')}
                </Text>
              </Pressable>
            ) : null}
            {showEmpty ? <Text style={ui.small}>{t('map.noData')}</Text> : null}
          </View>
        ) : null}
        <Toast message={toast} onHide={hideToast} />
      </View>

      <View style={styles.bottom} pointerEvents="box-none">
        <Legend />
        {cells.length ? <NightSummary key={nightDate} cells={cells} onOpen={selectCell} /> : null}
      </View>

      {nights ? (
        <NightPicker
          open={pickerOpen}
          onClose={() => setPickerOpen(false)}
          available={nights.available}
          latest={nights.latest}
          selected={nightDate}
          onSelect={pickNight}
        />
      ) : null}

      <CellSheet cell={selected} nightDate={nightDate} onClose={closeSheet} />
    </View>
  );
}

// One plain sentence with the highest risk of the night, big enough to read outdoors.
// Tapping it opens that place.
function NightSummary({ cells, onOpen }: { cells: Cell[]; onOpen: (c: Cell) => void }) {
  const { t } = useI18n();
  const top = cells.reduce((a, c) => (c.probability > a.probability ? c : a));
  const allLow = top.level === 'low';
  const message = allLow
    ? t('map.allLow', { n: cells.length })
    : t('map.highest', { level: t(`level.${top.level}`), place: top.name });
  return (
    <FadeIn>
      <Pressable
        accessibilityRole="button"
        accessibilityHint={t('map.tapForDetails')}
        onPress={() => onOpen(top)}
        style={({ pressed }) => [styles.summary, { borderLeftColor: levelColors[top.level] }, pressed && { opacity: 0.85 }]}
      >
        <View style={[styles.summaryIcon, { backgroundColor: levelColors[top.level] }]}>
          <Icon name={levelIcons[top.level]} size={26} color={levelOnColors[top.level]} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.summaryText}>{message}</Text>
          <Text style={ui.small}>{t('map.tapForDetails')}</Text>
        </View>
        <Icon name="chevron-right" size={24} color={colors.muted} />
      </Pressable>
    </FadeIn>
  );
}

const Legend = memo(function Legend() {
  const { t } = useI18n();
  return (
    <View style={styles.legend}>
      <Text style={ui.label}>{t('map.legend')}</Text>
      {LEVELS.map((l) => (
        <View key={l} style={styles.legendRow}>
          <View style={[styles.swatch, { backgroundColor: levelColors[l] }]}>
            <Icon name={levelIcons[l]} size={10} color={levelOnColors[l]} />
          </View>
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
});

function CellSheet({ cell, nightDate, onClose }: { cell: Cell | null; nightDate?: string; onClose: () => void }) {
  const { t, formatDateLong } = useI18n();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={!!cell} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={t('common.close')} />
      {cell ? (
        <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
          <View style={styles.handle} />
          <ScrollView contentContainerStyle={{ gap: spacing.md, paddingBottom: spacing.md }}>
            <Text style={ui.title}>{cell.name}</Text>
            <ReanalysisNote nightDate={nightDate} />
            <FadeIn>
              <RiskMeter level={cell.level} probability={cell.probability} />
            </FadeIn>
            {/* Plain observed outcome of that night (from the data, not from Muse). */}
            <View style={styles.observed}>
              <Icon name="thermometer-low" size={22} color={colors.primary} />
              <Text style={[ui.body, { flex: 1 }]}>
                {cell.observed
                  ? t(cell.observed.frost ? 'map.frostObserved' : 'map.noFrostObserved', { t: cell.observed.tmin_c })
                  : t('map.notYetKnown')}
              </Text>
            </View>
            {nightDate ? (
              <MuseExplanation pointId={cell.point_id} nightDate={nightDate} />
            ) : (
              <SpeakButton
                text={t('map.speakSummary', { place: cell.name, level: t(`level.${cell.level}`), p: percent(cell.probability) })}
              />
            )}
            <TechnicalInfo>
              <Text style={ui.small}>{t('map.elevation', { m: Math.round(cell.elevation_m) })}</Text>
              {nightDate ? <Text style={ui.small}>{t('common.night', { date: formatDateLong(nightDate) })}</Text> : null}
              <SectionTitle>{t('map.drivers')}</SectionTitle>
              <DriversList drivers={cell.top_drivers} />
              <SectionTitle>{t('map.conditions')}</SectionTitle>
              <ConditionsList conditions={cell.conditions_1800} />
              <SectionTitle>{t('map.reliability')}</SectionTitle>
              <ReliabilityText reliability={cell.historical_reliability} />
            </TechnicalInfo>
            <Button label={t('common.close')} onPress={onClose} variant="secondary" />
          </ScrollView>
        </View>
      ) : null}
    </Modal>
  );
}

export function MapEmptyFallback() {
  const { t } = useI18n();
  return <EmptyView message={t('map.noData')} />;
}

export { ExplanationLabel, ReplayTag };

const styles = StyleSheet.create({
  cellWrap: { padding: 18, alignItems: 'center', justifyContent: 'center' },
  cellDot: {
    minWidth: 58,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 3,
    paddingHorizontal: 6,
    borderWidth: 2,
    borderColor: colors.pinBorder,
    shadowColor: colors.mapShadow,
    shadowOpacity: 1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  cellText: { fontWeight: '800', fontSize: 15 },
  top: { position: 'absolute', left: spacing.md, right: spacing.md, gap: spacing.sm },
  controlsRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  leftControls: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, flexShrink: 1 },
  rightControls: { gap: spacing.sm },
  status: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderRadius: 10,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  // Leaves the bottom strip free for the map logo and attribution (Apple, Google, Esri, OSM).
  bottom: { position: 'absolute', left: spacing.md, right: spacing.md, bottom: 30, gap: spacing.sm },
  summary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: 14,
    borderLeftWidth: 8,
    padding: spacing.md,
    minHeight: 72,
    shadowColor: colors.cardShadow,
    shadowOpacity: 1,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  summaryIcon: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  summaryText: { color: colors.text, fontSize: 18, fontWeight: '700' },
  legend: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: spacing.sm,
    gap: 3,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendText: { fontSize: 13, color: colors.text },
  swatch: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.pinBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backdrop: { flex: 1, backgroundColor: colors.backdrop },
  sheet: {
    maxHeight: '88%',
    backgroundColor: colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
  },
  observed: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.beige,
    borderRadius: 12,
    padding: spacing.md,
  },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: spacing.sm },
});
