import { router, Stack } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, type MapPressEvent, type MapViewHandle, type Region } from '@/ui/maps';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, ApiError, type Channels, type Threshold } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { fromPolygon, polygonInsideCoverage, toPolygon, type LatLng } from '@/geo';
import type { PlaceResult } from '@/geo/search';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import { haptic } from '@/ui/feedback';
import { Icon } from '@/ui/icons';
import { Button, ErrorView, errorText, Field, LoadingView, SectionTitle, ToggleRow, styles as ui } from '@/ui/components';
import { nativeMapType, useMapLayer } from '@/ui/mapLayer';
import { LocateControl, RoundButton, TempPin, Toast } from '@/ui/MapOverlay';
import { MapSearch } from '@/ui/MapSearch';
import { CoverageLabels, HaloPolygon, HaloPolyline } from '@/ui/mapShapes';
import { ThresholdField } from '@/ui/ThresholdField';
import { colors, spacing } from '@/ui/theme';

const MAX_VERTICES = 12;
// Close view where houses and fields are visible.
const CLOSE_DELTA = 0.01;
const CAMERA_MS = 450;

// Add: a tap on the map adds a vertex. Move: tap a vertex, then tap where it goes (or
// drag it). Delete: tap a vertex to remove it.
type Mode = 'add' | 'move' | 'delete';
const FULL_REGION: Region = { latitude: -17.4, longitude: -68.1, latitudeDelta: 2.7, longitudeDelta: 3.5 };

function midpoint(a: LatLng, b: LatLng): LatLng {
  return { latitude: (a.latitude + b.latitude) / 2, longitude: (a.longitude + b.longitude) / 2 };
}

export default function DrawZoneScreen() {
  const { t } = useI18n();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const coverage = useAsync(() => api.getCoverage(), []);
  const mapRef = useRef<MapViewHandle | null>(null);
  const { layer, toggle: toggleLayer } = useMapLayer();
  const [pin, setPin] = useState<LatLng | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const hideToast = useCallback(() => setToast(null), []);
  const hidePin = useCallback(() => setPin(null), []);

  const goTo = useCallback((point: LatLng) => {
    setPin(point);
    mapRef.current?.animateToRegion({ ...point, latitudeDelta: CLOSE_DELTA, longitudeDelta: CLOSE_DELTA }, CAMERA_MS);
  }, []);

  const [mode, setMode] = useState<Mode>('add');
  const [trackHandles, setTrackHandles] = useState(false);

  const [step, setStep] = useState<'draw' | 'form'>('draw');
  const [vertices, setVertices] = useState<LatLng[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  // Native maps cache marker views; redraw the handles briefly when their color changes.
  useEffect(() => {
    setTrackHandles(true);
    const timer = setTimeout(() => setTrackHandles(false), 300);
    return () => clearTimeout(timer);
  }, [mode, selected]);
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [threshold, setThreshold] = useState<Threshold>(user?.default_threshold ?? 50);
  const [channels, setChannels] = useState<Channels>({ push: true, email: true });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const valid = useMemo(() => {
    if (!coverage.data || vertices.length < 3) return false;
    return polygonInsideCoverage(vertices, coverage.data);
  }, [vertices, coverage.data]);

  const showInvalid = vertices.length >= 3 && !!coverage.data && !valid;

  const midpoints = useMemo(() => {
    if (vertices.length < 2) return [];
    const closed = vertices.length >= 3;
    const count = closed ? vertices.length : vertices.length - 1;
    return Array.from({ length: count }, (_, i) => {
      const a = vertices[i];
      const b = vertices[(i + 1) % vertices.length];
      return { point: midpoint(a, b), insertAt: i + 1 };
    });
  }, [vertices]);

  function tapMap(e: MapPressEvent) {
    const point = e.nativeEvent.coordinate;
    if (mode === 'move') {
      if (selected === null) return;
      haptic.select();
      moveVertex(selected, point);
      setSelected(null);
      return;
    }
    if (mode === 'delete') return;
    if (vertices.length >= MAX_VERTICES) {
      setNotice(t('draw.maxReached'));
      return;
    }
    haptic.tap();
    setNotice(null);
    setVertices([...vertices, point]);
  }

  function moveVertex(index: number, coord: LatLng) {
    setVertices((prev) => prev.map((v, i) => (i === index ? coord : v)));
  }

  // Drag events arrive many times per frame; apply at most one update per frame so the
  // map stays smooth while a vertex moves.
  const dragFrame = useRef<number | null>(null);
  const dragPending = useRef<{ index: number; coord: LatLng } | null>(null);
  function dragVertex(index: number, coord: LatLng) {
    dragPending.current = { index, coord };
    if (dragFrame.current !== null) return;
    dragFrame.current = requestAnimationFrame(() => {
      dragFrame.current = null;
      const pending = dragPending.current;
      if (pending) moveVertex(pending.index, pending.coord);
    });
  }

  function pressVertex(index: number) {
    if (mode === 'delete') {
      haptic.warning();
      setVertices((prev) => prev.filter((_, i) => i !== index));
      setSelected(null);
      setNotice(null);
      return;
    }
    if (mode === 'move') {
      haptic.select();
      setSelected(selected === index ? null : index);
    }
  }

  function changeMode(next: Mode) {
    haptic.select();
    setMode(next);
    setSelected(null);
    setNotice(null);
  }

  // Static layers are built once, so panning or adding vertices never re-sends the 8
  // coverage circles to the native map.
  const coverageLayer = useMemo(
    () =>
      coverage.data?.features.map((f) => (
        <HaloPolygon
          key={f.properties.point_id}
          coordinates={fromPolygon(f.geometry)}
          fillColor={colors.coverageFill}
          strokeColor={colors.coverageStroke}
          strokeWidth={1.5}
        />
      )),
    [coverage.data],
  );

  function insertVertex(at: number, point: LatLng) {
    if (vertices.length >= MAX_VERTICES) {
      setNotice(t('draw.maxReached'));
      return;
    }
    setNotice(null);
    setSelected(null);
    setVertices((prev) => [...prev.slice(0, at), point, ...prev.slice(at)]);
  }

  function finish() {
    if (!coverage.data || vertices.length < 3) return;
    if (!polygonInsideCoverage(vertices, coverage.data)) {
      setNotice(`${t('draw.outside')}. ${t('draw.outsideBody')}`);
      return;
    }
    setNotice(null);
    setStep('form');
  }

  async function save() {
    if (!name.trim()) {
      setFormError(t('draw.nameRequired'));
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await api.createAoi({ name: name.trim(), polygon: toPolygon(vertices), threshold, channels });
      router.back();
    } catch (err) {
      setFormError(err instanceof ApiError && err.status === 422 ? t('draw.outside') : errorText(t, err));
      setSaving(false);
    }
  }

  const header = (
    <Stack.Screen
      options={{
        title: step === 'draw' ? t('draw.title') : t('draw.formTitle'),
        headerStyle: { backgroundColor: colors.headerBg },
        headerTintColor: colors.headerText,
        headerLeft: () => (
          <Pressable onPress={() => (step === 'form' ? setStep('draw') : router.back())} hitSlop={8}>
            <Text style={styles.headerLink}>{step === 'form' ? t('common.back') : t('common.cancel')}</Text>
          </Pressable>
        ),
      }}
    />
  );

  if (coverage.loading && !coverage.data) return <>{header}<LoadingView /></>;
  if (coverage.error || !coverage.data) return <>{header}<ErrorView error={coverage.error} onRetry={coverage.reload} /></>;

  if (step === 'form') {
    return (
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        {header}
        <ScrollView contentContainerStyle={styles.form}>
          <Field
            label={t('draw.nameLabel')}
            placeholder={t('draw.namePlaceholder')}
            value={name}
            onChangeText={setName}
            maxLength={60}
            autoFocus
          />
          <ThresholdField value={threshold} onChange={setThreshold} />
          <SectionTitle>{t('draw.channelsLabel')}</SectionTitle>
          <ToggleRow label={t('zones.push')} value={channels.push} onChange={(push) => setChannels({ ...channels, push })} />
          <ToggleRow label={t('zones.email')} value={channels.email} onChange={(email) => setChannels({ ...channels, email })} />
          {formError ? <Text style={ui.errorText}>{formError}</Text> : null}
          <Button label={t('draw.saveZone')} onPress={save} loading={saving} />
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  const hint =
    mode === 'move'
      ? selected === null
        ? t('draw.movePickHint')
        : t('draw.moveHint')
      : mode === 'delete'
        ? t('draw.deleteHint')
        : vertices.length >= 2
          ? t('draw.midHint')
          : t('draw.hint');
  const stroke = showInvalid ? colors.drawInvalid : colors.drawStroke;

  return (
    <View style={{ flex: 1 }}>
      {header}
      <View style={{ flex: 1 }}>
      <MapView
        ref={mapRef}
        style={{ flex: 1 }}
        initialRegion={FULL_REGION}
        onPress={tapMap}
        mapType={nativeMapType(layer)}
        showsPointsOfInterests={false}
        rotateEnabled={false}
        pitchEnabled={false}
        toolbarEnabled={false}
        moveOnMarkerPress={false}
      >
        {coverageLayer}
        <CoverageLabels coverage={coverage.data} />
        {vertices.length >= 3 ? (
          <HaloPolygon coordinates={vertices} fillColor={colors.aoiFill} strokeColor={stroke} strokeWidth={2.5} />
        ) : vertices.length === 2 ? (
          <HaloPolyline coordinates={vertices} strokeColor={stroke} strokeWidth={2.5} />
        ) : null}
        {pin ? (
          <Marker coordinate={pin} anchor={{ x: 0.5, y: 1 }} tracksViewChanges>
            <TempPin onDone={hidePin} />
          </Marker>
        ) : null}
        {vertices.map((v, i) => (
          <Marker
            key={`v-${i}`}
            coordinate={v}
            anchor={{ x: 0.5, y: 0.5 }}
            draggable={mode === 'move'}
            onDragStart={() => haptic.select()}
            onDrag={(e) => dragVertex(i, e.nativeEvent.coordinate)}
            onDragEnd={(e) => moveVertex(i, e.nativeEvent.coordinate)}
            onPress={() => pressVertex(i)}
            // Redraw the handle when its look changes with the mode or the selection.
            tracksViewChanges={trackHandles}
            zIndex={3}
          >
            <View style={styles.vertexHit}>
              <View
                style={[
                  styles.vertex,
                  mode === 'delete' && styles.vertexDelete,
                  selected === i && styles.vertexSelected,
                ]}
              />
            </View>
          </Marker>
        ))}
        {mode === 'add' && midpoints.map((m, k) => (
          <Marker
            key={`m-${k}`}
            coordinate={m.point}
            anchor={{ x: 0.5, y: 0.5 }}
            onPress={() => {
              haptic.tap();
              insertVertex(m.insertAt, m.point);
            }}
            tracksViewChanges={false}
            zIndex={2}
          >
            <View style={styles.vertexHit}>
              <View style={styles.midpoint} />
            </View>
          </Marker>
        ))}
      </MapView>
      <View style={styles.top} pointerEvents="box-none">
        <MapSearch
          coverage={coverage.data}
          allowOutside={false}
          onSelect={(place: PlaceResult) => goTo({ latitude: place.latitude, longitude: place.longitude })}
        />
        <View style={styles.rightControls} pointerEvents="box-none">
          <RoundButton
            icon="layers"
            label={t('map.switchLayer', { layer: t(layer === 'satellite' ? 'map.layerMap' : 'map.layerSatellite') })}
            onPress={toggleLayer}
          />
          <LocateControl onLocated={goTo} onMessage={setToast} />
        </View>
        <Toast message={toast} onHide={hideToast} />
      </View>
      </View>
      <View style={[styles.toolbar, { paddingBottom: insets.bottom + spacing.md }]}>
        <View style={styles.modes}>
          {(
            [
              ['add', 'plus', 'draw.modeAdd'],
              ['move', 'edit', 'draw.modeMove'],
              ['delete', 'trash', 'draw.modeDelete'],
            ] as const
          ).map(([id, icon, label]) => {
            const on = mode === id;
            return (
              <Pressable
                key={id}
                accessibilityRole="button"
                accessibilityState={{ selected: on }}
                accessibilityLabel={t(label)}
                onPress={() => changeMode(id)}
                style={({ pressed }) => [
                  styles.mode,
                  on && (id === 'delete' ? styles.modeOnDanger : styles.modeOn),
                  pressed && { opacity: 0.85 },
                ]}
              >
                <Icon name={icon} size={24} color={on ? colors.primaryText : id === 'delete' ? colors.danger : colors.primary} />
                <Text style={[styles.modeText, on && styles.modeTextOn, !on && id === 'delete' && { color: colors.danger }]}>
                  {t(label)}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.hintRow}>
          <Text style={[ui.body, { flex: 1 }]}>{hint}</Text>
          <View style={styles.countChip}>
            <Text style={styles.countText}>{t('draw.vertices', { n: vertices.length })}</Text>
          </View>
        </View>
        {showInvalid ? <Text style={ui.errorText}>{t('draw.invalidOutside')}</Text> : null}
        {notice ? <Text style={ui.errorText}>{notice}</Text> : null}
        <View style={styles.buttons}>
          <Button
            label={t('draw.undo')}
            variant="secondary"
            disabled={!vertices.length}
            onPress={() => {
              setNotice(null);
              setSelected(null);
              setVertices(vertices.slice(0, -1));
            }}
            style={{ flex: 1 }}
          />
          <Button
            label={t('draw.clear')}
            variant="secondary"
            disabled={!vertices.length}
            onPress={() => {
              setNotice(null);
              setSelected(null);
              setVertices([]);
            }}
            style={{ flex: 1 }}
          />
          <Button label={t('draw.finish')} disabled={!valid} onPress={finish} style={{ flex: 1 }} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  headerLink: { color: colors.headerText, fontSize: 16 },
  top: { position: 'absolute', top: spacing.sm, left: spacing.md, right: spacing.md, gap: spacing.sm },
  rightControls: { alignSelf: 'flex-end', gap: spacing.sm },
  // Large invisible touch area around each handle, easy to hit with a finger.
  vertexHit: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  modes: { flexDirection: 'row', gap: spacing.sm },
  mode: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
    minHeight: 60,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  modeOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  modeOnDanger: { backgroundColor: colors.danger, borderColor: colors.danger },
  modeText: { color: colors.primary, fontWeight: '700', fontSize: 14 },
  modeTextOn: { color: colors.primaryText },
  hintRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  countChip: {
    backgroundColor: colors.navButtonBg,
    borderRadius: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  countText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  vertex: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.aoiStroke,
    borderWidth: 3,
    borderColor: colors.mapHalo,
    shadowColor: colors.mapShadow,
    shadowOpacity: 1,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 3,
  },
  vertexDelete: { backgroundColor: colors.danger },
  vertexSelected: { backgroundColor: colors.danger, width: 26, height: 26, borderRadius: 13 },
  midpoint: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.mapHalo,
    borderWidth: 2,
    borderColor: colors.aoiStroke,
  },
  toolbar: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    gap: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  buttons: { flexDirection: 'row', gap: spacing.sm },
  form: { padding: spacing.xl, gap: spacing.md },
});
