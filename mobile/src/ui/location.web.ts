// Web version of ./location.ts with navigator.geolocation (local testing only).
import type { LatLng } from '@/geo';

export type LocationResult = { ok: true; coordinate: LatLng } | { ok: false; reason: 'denied' | 'unavailable' };

export function currentLocation(): Promise<LocationResult> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({ ok: false, reason: 'unavailable' });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ ok: true, coordinate: { latitude: p.coords.latitude, longitude: p.coords.longitude } }),
      (err) => resolve({ ok: false, reason: err.code === err.PERMISSION_DENIED ? 'denied' : 'unavailable' }),
      { timeout: 15000, maximumAge: 60000 },
    );
  });
}
