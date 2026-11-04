// One-off foreground location, only when the user taps "My location". The position is
// used to move the camera and is never stored or sent to the backend.
import * as Location from 'expo-location';

import type { LatLng } from '@/geo';

export type LocationResult = { ok: true; coordinate: LatLng } | { ok: false; reason: 'denied' | 'unavailable' };

export async function currentLocation(): Promise<LocationResult> {
  try {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== 'granted') return { ok: false, reason: 'denied' };
    const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
    return { ok: true, coordinate: { latitude: position.coords.latitude, longitude: position.coords.longitude } };
  } catch {
    return { ok: false, reason: 'unavailable' };
  }
}
