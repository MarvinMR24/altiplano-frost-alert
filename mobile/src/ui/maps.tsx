// Native maps (iOS in Expo Go). The web build resolves ./maps.web.tsx instead, because
// react-native-maps has no web implementation.
export { default, Marker, Polygon, Polyline } from 'react-native-maps';
export type { MapPressEvent, Region } from 'react-native-maps';
