// Native maps. Android uses Google Maps (Maps SDK for Android; the API key comes from
// app.config.ts), iOS keeps Apple Maps (Expo Go). The web build resolves ./maps.web.tsx
// instead (Leaflet), because react-native-maps has no web implementation.
import { forwardRef } from 'react';
import { Platform } from 'react-native';
import RNMapView, { PROVIDER_GOOGLE, type MapViewProps } from 'react-native-maps';

const MapView = forwardRef<RNMapView, MapViewProps>(function MapView(props, ref) {
  return <RNMapView ref={ref} provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined} {...props} />;
});

export default MapView;
export { Marker, Polygon, Polyline } from 'react-native-maps';
export type { MapPressEvent, MarkerDragStartEndEvent as MarkerDragEvent, Region } from 'react-native-maps';
export type MapViewHandle = RNMapView;
