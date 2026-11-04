// Web stand-in for react-native-maps, used for local testing in the browser.
// It wraps Leaflet with Esri World Imagery (mapType "hybrid" or "satellite") or the standard
// OpenStreetMap tiles (any other mapType), no API key, and supports what the
// screens use: polygons, polylines, markers with custom React children, marker taps,
// draggable markers, map taps that return a coordinate and animateToRegion on the ref.
// The iPhone build uses ./maps.tsx (react-native-maps, Apple Maps).
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import {
  createContext,
  forwardRef,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors } from './theme';

type LatLng = { latitude: number; longitude: number };

export type Region = LatLng & { latitudeDelta: number; longitudeDelta: number };
export type MapPressEvent = { nativeEvent: { coordinate: LatLng } };
export type MarkerDragEvent = { nativeEvent: { coordinate: LatLng } };

export type MapViewHandle = { animateToRegion: (region: Region, durationMs?: number) => void };

const OSM_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const ESRI_IMAGERY_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_LABELS_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';
const ESRI_ATTRIBUTION = 'Imagery: Esri, Maxar, Earthstar Geographics and the GIS User Community';

function isSatellite(mapType?: string): boolean {
  return mapType === 'hybrid' || mapType === 'satellite';
}

// Rural areas have no level 19 imagery: upscale level 18 instead of showing blank tiles.
function baseLayers(mapType?: string): L.TileLayer[] {
  if (isSatellite(mapType)) {
    return [
      L.tileLayer(ESRI_IMAGERY_URL, { attribution: ESRI_ATTRIBUTION, maxZoom: 19, maxNativeZoom: 18 }),
      L.tileLayer(ESRI_LABELS_URL, { maxZoom: 19, maxNativeZoom: 18 }),
    ];
  }
  return [L.tileLayer(OSM_URL, { attribution: OSM_ATTRIBUTION, maxZoom: 19 })];
}

const MapContext = createContext<L.Map | null>(null);

function regionBounds(r: Region): L.LatLngBoundsExpression {
  return [
    [r.latitude - r.latitudeDelta / 2, r.longitude - r.longitudeDelta / 2],
    [r.latitude + r.latitudeDelta / 2, r.longitude + r.longitudeDelta / 2],
  ];
}

function toLatLng(p: LatLng): L.LatLngExpression {
  return [p.latitude, p.longitude];
}

function fromLeaflet(p: L.LatLng): LatLng {
  return { latitude: p.lat, longitude: p.lng };
}

type MapViewProps = {
  style?: StyleProp<ViewStyle>;
  initialRegion: Region;
  onPress?: (e: MapPressEvent) => void;
  onRegionChangeComplete?: (region: Region) => void;
  children?: ReactNode;
  // Native-only props are accepted and ignored on the web.
  moveOnMarkerPress?: boolean;
  mapType?: string;
  showsCompass?: boolean;
  showsPointsOfInterests?: boolean;
  rotateEnabled?: boolean;
  pitchEnabled?: boolean;
  toolbarEnabled?: boolean;
};

const MapView = forwardRef<MapViewHandle, MapViewProps>(function MapView(
  { style, initialRegion, onPress, onRegionChangeComplete, mapType, children },
  ref,
) {
  const container = useRef<HTMLDivElement | null>(null);
  const [map, setMap] = useState<L.Map | null>(null);
  const onPressRef = useRef(onPress);
  onPressRef.current = onPress;
  const onRegionRef = useRef(onRegionChangeComplete);
  onRegionRef.current = onRegionChangeComplete;

  useEffect(() => {
    if (!container.current) return;
    // No zoom buttons: the search bar sits at the top; wheel and pinch zoom still work.
    const m = L.map(container.current, { zoomControl: false, attributionControl: true, zoomSnap: 0.25, maxZoom: 19 });
    m.fitBounds(regionBounds(initialRegion));
    m.on('click', (e: L.LeafletMouseEvent) => onPressRef.current?.({ nativeEvent: { coordinate: fromLeaflet(e.latlng) } }));
    m.on('moveend', () => {
      const b = m.getBounds();
      const c = b.getCenter();
      onRegionRef.current?.({
        latitude: c.lat,
        longitude: c.lng,
        latitudeDelta: b.getNorth() - b.getSouth(),
        longitudeDelta: b.getEast() - b.getWest(),
      });
    });
    const observer = new ResizeObserver(() => m.invalidateSize());
    observer.observe(container.current);
    setMap(m);
    return () => {
      observer.disconnect();
      m.remove();
    };
    // The initial region is applied once, like react-native-maps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;
    const layers = baseLayers(mapType);
    layers.forEach((l) => l.addTo(map));
    return () => layers.forEach((l) => l.remove());
  }, [map, mapType]);

  useEffect(() => {
    if (container.current) container.current.style.cursor = onPress ? 'crosshair' : '';
  }, [onPress]);

  useImperativeHandle(
    ref,
    () => ({
      animateToRegion: (region: Region, durationMs = 500) => {
        map?.flyToBounds(regionBounds(region), { duration: durationMs / 1000 });
      },
    }),
    [map],
  );

  return (
    <View style={[styles.container, style]}>
      <div ref={container} style={{ position: 'absolute', inset: 0 }} />
      {map ? <MapContext.Provider value={map}>{children}</MapContext.Provider> : null}
    </View>
  );
});

export default MapView;

type ShapeProps = {
  coordinates: LatLng[];
  strokeColor?: string;
  strokeWidth?: number;
  fillColor?: string;
  tappable?: boolean;
};

function useShape(kind: 'polygon' | 'polyline', props: ShapeProps) {
  const map = useContext(MapContext);
  const layer = useRef<L.Polygon | L.Polyline | null>(null);
  const { coordinates, strokeColor = colors.drawStroke, strokeWidth = 1, fillColor } = props;
  const options = useMemo<L.PolylineOptions>(
    () => ({
      color: strokeColor,
      weight: strokeWidth,
      opacity: 1,
      fill: kind === 'polygon' && !!fillColor,
      fillColor,
      fillOpacity: 1,
      interactive: false,
    }),
    [kind, strokeColor, strokeWidth, fillColor],
  );

  useEffect(() => {
    if (!map) return;
    const latlngs = coordinates.map(toLatLng);
    const created = kind === 'polygon' ? L.polygon(latlngs, options) : L.polyline(latlngs, options);
    created.addTo(map);
    layer.current = created;
    return () => {
      created.remove();
      layer.current = null;
    };
    // Created once per map; updates below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, kind]);

  useEffect(() => {
    layer.current?.setLatLngs(coordinates.map(toLatLng));
  }, [coordinates]);

  useEffect(() => {
    layer.current?.setStyle(options);
  }, [options]);
}

export function Polygon(props: ShapeProps) {
  useShape('polygon', props);
  return null;
}

export function Polyline(props: ShapeProps) {
  useShape('polyline', props);
  return null;
}

type MarkerProps = {
  coordinate: LatLng;
  onPress?: () => void;
  anchor?: { x: number; y: number };
  draggable?: boolean;
  onDragStart?: () => void;
  onDrag?: (e: MarkerDragEvent) => void;
  onDragEnd?: (e: MarkerDragEvent) => void;
  tracksViewChanges?: boolean;
  zIndex?: number;
  children?: ReactNode;
};

export function Marker({ coordinate, onPress, anchor = { x: 0.5, y: 1 }, draggable, onDrag, onDragEnd, zIndex, children }: MarkerProps) {
  const map = useContext(MapContext);
  const marker = useRef<L.Marker | null>(null);
  const element = useMemo(() => document.createElement('div'), []);
  const handlers = useRef({ onPress, onDrag, onDragEnd });
  handlers.current = { onPress, onDrag, onDragEnd };

  useEffect(() => {
    if (!map) return;
    const icon = L.divIcon({ html: element, className: 'fw-marker', iconSize: [0, 0] });
    const m = L.marker(toLatLng(coordinate), { icon, draggable: !!draggable, zIndexOffset: zIndex ?? 0, keyboard: false });
    m.on('click', (e) => {
      L.DomEvent.stopPropagation(e);
      handlers.current.onPress?.();
    });
    m.on('drag', () => handlers.current.onDrag?.({ nativeEvent: { coordinate: fromLeaflet(m.getLatLng()) } }));
    m.on('dragend', () => handlers.current.onDragEnd?.({ nativeEvent: { coordinate: fromLeaflet(m.getLatLng()) } }));
    m.addTo(map);
    marker.current = m;
    return () => {
      m.remove();
      marker.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, element]);

  useEffect(() => {
    const m = marker.current;
    if (!m) return;
    const current = m.getLatLng();
    if (current.lat !== coordinate.latitude || current.lng !== coordinate.longitude) {
      m.setLatLng(toLatLng(coordinate));
    }
  }, [coordinate]);

  useEffect(() => {
    const m = marker.current;
    if (!m || !m.dragging) return;
    if (draggable) m.dragging.enable();
    else m.dragging.disable();
  }, [draggable]);

  const content = (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${-anchor.x * 100}%, ${-anchor.y * 100}%)`,
        cursor: draggable ? 'grab' : onPress ? 'pointer' : 'default',
      }}
    >
      {children ?? <View style={styles.pin} />}
    </div>
  );
  return createPortal(content, element);
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.sand, overflow: 'hidden' },
  pin: { width: 14, height: 14, borderRadius: 7, backgroundColor: colors.red, borderWidth: 2, borderColor: colors.pinBorder },
});
