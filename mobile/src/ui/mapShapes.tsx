// Map shapes with a light halo drawn under the colored stroke, so coverage circles, zones
// and the drawing line stay visible on dark satellite imagery.
import { memo, useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { CoverageFeature, CoverageResponse } from '@/api/client';
import { Marker, Polygon, Polyline } from '@/ui/maps';
import { fromPolygon, type LatLng } from '@/geo';
import { colors } from './theme';

const HALO_EXTRA = 3;

export function HaloPolygon({
  coordinates,
  strokeColor,
  strokeWidth,
  fillColor,
}: {
  coordinates: LatLng[];
  strokeColor: string;
  strokeWidth: number;
  fillColor: string;
}) {
  return (
    <>
      <Polygon
        coordinates={coordinates}
        strokeColor={colors.mapHalo}
        strokeWidth={strokeWidth + HALO_EXTRA}
        fillColor={colors.transparent}
        tappable={false}
      />
      <Polygon
        coordinates={coordinates}
        strokeColor={strokeColor}
        strokeWidth={strokeWidth}
        fillColor={fillColor}
        tappable={false}
      />
    </>
  );
}

export function HaloPolyline({ coordinates, strokeColor, strokeWidth }: { coordinates: LatLng[]; strokeColor: string; strokeWidth: number }) {
  return (
    <>
      <Polyline coordinates={coordinates} strokeColor={colors.mapHalo} strokeWidth={strokeWidth + HALO_EXTRA} />
      <Polyline coordinates={coordinates} strokeColor={strokeColor} strokeWidth={strokeWidth} />
    </>
  );
}

// Name of each covered place, pinned to the top edge of its coverage circle so it never
// covers the level marker in the center.
export const CoverageLabels = memo(function CoverageLabels({
  coverage,
  onPress,
}: {
  coverage: CoverageResponse;
  onPress?: (feature: CoverageFeature, center: LatLng) => void;
}) {
  // Native maps snapshot custom markers; keep tracking briefly so the text is laid out
  // before the snapshot (Android can otherwise draw an empty or clipped label).
  const [tracking, setTracking] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setTracking(false), 800);
    return () => clearTimeout(timer);
  }, [coverage]);
  // Computed once per coverage so map gestures never re-send coordinates to the native map.
  const labels = useMemo(
    () =>
      coverage.features.map((f) => {
        const ring = fromPolygon(f.geometry);
        const top = ring.reduce((a, p) => (p.latitude > a.latitude ? p : a), ring[0]);
        const center = {
          latitude: ring.reduce((s, p) => s + p.latitude, 0) / ring.length,
          longitude: ring.reduce((s, p) => s + p.longitude, 0) / ring.length,
        };
        return { feature: f, top, center };
      }),
    [coverage],
  );
  return (
    <>
      {labels.map(({ feature, top, center }) => (
        <Marker
          key={`label-${feature.properties.point_id}`}
          coordinate={top}
          anchor={{ x: 0.5, y: 0.5 }}
          tracksViewChanges={tracking}
          onPress={onPress ? () => onPress(feature, center) : undefined}
          zIndex={1}
        >
          <View style={[styles.label, onPress && styles.labelTappable]}>
            <Text style={styles.labelText} numberOfLines={1}>
              {feature.properties.name}
            </Text>
          </View>
        </Marker>
      ))}
    </>
  );
});

const styles = StyleSheet.create({
  label: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.coverageStroke,
    paddingHorizontal: 8,
    paddingVertical: 3,
    shadowColor: colors.mapShadow,
    shadowOpacity: 1,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 3,
  },
  labelTappable: { paddingHorizontal: 12, paddingVertical: 6, borderWidth: 2 },
  labelText: { color: colors.primary, fontSize: 13, fontWeight: '700' },
});
