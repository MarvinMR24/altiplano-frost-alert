// Web stand-in for react-native-maps, used only for local testing in the browser.
// It draws a schematic map (no base map tiles): an equirectangular projection of the
// initial region with a 0.5 degree grid. It supports what the screens use: polygons,
// polylines, markers with custom children, marker taps and map taps that return a
// coordinate. No pan or zoom.
import { createContext, useContext, useState, type MouseEvent, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View, type LayoutChangeEvent, type StyleProp, type ViewStyle } from 'react-native';

import { useI18n } from '@/i18n';

type LatLng = { latitude: number; longitude: number };

export type Region = LatLng & { latitudeDelta: number; longitudeDelta: number };
export type MapPressEvent = { nativeEvent: { coordinate: LatLng } };

type Projection = {
  width: number;
  height: number;
  toXY: (p: LatLng) => { x: number; y: number };
};

const ProjectionContext = createContext<Projection | null>(null);

function makeProjection(region: Region, width: number, height: number): Projection & { toLatLng: (x: number, y: number) => LatLng } {
  // Degrees of longitude are shorter than degrees of latitude away from the equator.
  const kx = Math.cos((region.latitude * Math.PI) / 180);
  // Zoom out a little so cells at the edge of the region and their coverage circles fit.
  const scale = Math.min(width / (region.longitudeDelta * kx), height / region.latitudeDelta) / 1.4;
  const cx = width / 2;
  const cy = height / 2;
  return {
    width,
    height,
    toXY: (p) => ({
      x: cx + (p.longitude - region.longitude) * kx * scale,
      y: cy - (p.latitude - region.latitude) * scale,
    }),
    toLatLng: (x, y) => ({
      latitude: region.latitude - (y - cy) / scale,
      longitude: region.longitude + (x - cx) / (kx * scale),
    }),
  };
}

type MapViewProps = {
  style?: StyleProp<ViewStyle>;
  initialRegion: Region;
  onPress?: (e: MapPressEvent) => void;
  children?: ReactNode;
};

export default function MapView({ style, initialRegion, onPress, children }: MapViewProps) {
  const { t } = useI18n();
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const projection = size ? makeProjection(initialRegion, size.width, size.height) : null;

  function onLayout(e: LayoutChangeEvent) {
    const { width, height } = e.nativeEvent.layout;
    setSize({ width, height });
  }

  function onClick(e: MouseEvent<HTMLDivElement>) {
    if (!onPress || !projection) return;
    const rect = e.currentTarget.getBoundingClientRect();
    onPress({ nativeEvent: { coordinate: projection.toLatLng(e.clientX - rect.left, e.clientY - rect.top) } });
  }

  return (
    <View style={[styles.container, style]} onLayout={onLayout}>
      {projection ? (
        <ProjectionContext.Provider value={projection}>
          <div style={{ position: 'absolute', inset: 0, cursor: onPress ? 'crosshair' : 'default' }} onClick={onClick}>
            <Grid region={initialRegion} />
            {children}
          </div>
        </ProjectionContext.Provider>
      ) : null}
      <View style={styles.badge} pointerEvents="none">
        <Text style={styles.badgeText}>{t('map.webPreview')}</Text>
      </View>
    </View>
  );
}

function Grid({ region }: { region: Region }) {
  const projection = useContext(ProjectionContext);
  if (!projection) return null;
  const { width, height, toXY } = projection;
  const lines: ReactNode[] = [];
  const step = 0.5;
  const span = Math.max(region.latitudeDelta, region.longitudeDelta) * 2;
  for (let v = Math.floor((region.latitude - span) / step) * step; v <= region.latitude + span; v += step) {
    const { y } = toXY({ latitude: v, longitude: region.longitude });
    lines.push(<line key={`lat${v}`} x1={0} x2={width} y1={y} y2={y} stroke="#C9D3DE" strokeWidth={1} />);
  }
  for (let v = Math.floor((region.longitude - span) / step) * step; v <= region.longitude + span; v += step) {
    const { x } = toXY({ latitude: region.latitude, longitude: v });
    lines.push(<line key={`lon${v}`} x1={x} x2={x} y1={0} y2={height} stroke="#C9D3DE" strokeWidth={1} />);
  }
  return (
    <svg width={width} height={height} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {lines}
    </svg>
  );
}

type ShapeProps = {
  coordinates: LatLng[];
  strokeColor?: string;
  strokeWidth?: number;
  fillColor?: string;
  tappable?: boolean;
};

function Shape({ coordinates, strokeColor = '#000', strokeWidth = 1, fillColor, closed }: ShapeProps & { closed: boolean }) {
  const projection = useContext(ProjectionContext);
  if (!projection || coordinates.length < 2) return null;
  const points = coordinates
    .map((c) => projection.toXY(c))
    .map((p) => `${p.x},${p.y}`)
    .join(' ');
  return (
    <svg width={projection.width} height={projection.height} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {closed ? (
        <polygon points={points} fill={fillColor ?? 'none'} stroke={strokeColor} strokeWidth={strokeWidth} />
      ) : (
        <polyline points={points} fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      )}
    </svg>
  );
}

export function Polygon(props: ShapeProps) {
  return <Shape {...props} closed />;
}

export function Polyline(props: ShapeProps) {
  return <Shape {...props} closed={false} />;
}

type MarkerProps = {
  coordinate: LatLng;
  onPress?: () => void;
  anchor?: { x: number; y: number };
  children?: ReactNode;
};

export function Marker({ coordinate, onPress, anchor = { x: 0.5, y: 1 }, children }: MarkerProps) {
  const projection = useContext(ProjectionContext);
  if (!projection) return null;
  const { x, y } = projection.toXY(coordinate);
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: `translate(${-anchor.x * 100}%, ${-anchor.y * 100}%)`,
        cursor: onPress ? 'pointer' : 'default',
        pointerEvents: onPress ? 'auto' : 'none',
      }}
      onClick={(e) => {
        e.stopPropagation();
        onPress?.();
      }}
    >
      {children ?? <Pressable style={styles.pin} />}
    </div>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: '#EEF3F8', overflow: 'hidden' },
  badge: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  badgeText: { fontSize: 11, color: '#3A3A3C' },
  pin: { width: 14, height: 14, borderRadius: 7, backgroundColor: '#D7263D', borderWidth: 2, borderColor: '#fff' },
});
