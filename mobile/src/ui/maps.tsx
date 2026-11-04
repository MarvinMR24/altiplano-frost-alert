// Native maps (iOS in Expo Go, Apple Maps). The web build resolves ./maps.web.tsx instead,
// because react-native-maps has no web implementation.
import MapView from 'react-native-maps';

export default MapView;
export { Marker, Polygon, Polyline } from 'react-native-maps';
export type { MapPressEvent, MarkerDragStartEndEvent as MarkerDragEvent, Region } from 'react-native-maps';
export type MapViewHandle = MapView;
