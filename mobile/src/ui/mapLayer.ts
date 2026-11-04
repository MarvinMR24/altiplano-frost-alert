// Base map layer shared by every map screen: satellite imagery (default) or street map.
// The choice is remembered per device.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

export type MapLayer = 'satellite' | 'map';

const STORAGE_KEY = 'frostwatch.mapLayer';
let current: MapLayer = 'satellite';
let loaded = false;
const listeners = new Set<(layer: MapLayer) => void>();

function publish(layer: MapLayer) {
  current = layer;
  listeners.forEach((l) => l(layer));
}

// react-native-maps type: hybrid is imagery plus place names. mutedStandard is iOS only.
export function nativeMapType(layer: MapLayer): 'hybrid' | 'mutedStandard' | 'standard' {
  if (layer === 'satellite') return 'hybrid';
  return Platform.OS === 'ios' ? 'mutedStandard' : 'standard';
}

export function useMapLayer(): { layer: MapLayer; toggle: () => void } {
  const [layer, setLayer] = useState<MapLayer>(current);
  useEffect(() => {
    listeners.add(setLayer);
    if (!loaded) {
      loaded = true;
      try {
        AsyncStorage.getItem(STORAGE_KEY)
          .then((stored) => {
            if (stored === 'satellite' || stored === 'map') publish(stored);
          })
          .catch(() => undefined);
      } catch {
        // Storage unavailable: keep the default.
      }
    }
    return () => {
      listeners.delete(setLayer);
    };
  }, []);
  function toggle() {
    const next: MapLayer = current === 'satellite' ? 'map' : 'satellite';
    publish(next);
    try {
      AsyncStorage.setItem(STORAGE_KEY, next).catch(() => undefined);
    } catch {
      // Not persisted; the choice still applies for this session.
    }
  }
  return { layer, toggle };
}
