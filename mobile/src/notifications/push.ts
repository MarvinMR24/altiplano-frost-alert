// Push notifications, guarded so the app never crashes where push is unavailable.
// Remote push does not work in Expo Go on Android (SDK 53+), so on that platform the
// expo-notifications module is never loaded.

import Constants, { ExecutionEnvironment } from 'expo-constants';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

import { EAS_PROJECT_ID } from '@/config';

type NotificationsModule = typeof import('expo-notifications');

export type PushPermission = 'granted' | 'denied' | 'unavailable';

const isExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;

export const pushSupported = Platform.OS === 'ios' || (Platform.OS === 'android' && !isExpoGo);

let cached: NotificationsModule | null | undefined;

function notifications(): NotificationsModule | null {
  if (cached !== undefined) return cached;
  if (!pushSupported) {
    cached = null;
    return cached;
  }
  try {
    cached = require('expo-notifications') as NotificationsModule;
  } catch {
    cached = null;
  }
  return cached;
}

export function configureForegroundHandler(): void {
  const N = notifications();
  if (!N) return;
  N.setNotificationHandler({
    handleNotification: async () => ({
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
}

export async function requestPushPermission(): Promise<PushPermission> {
  const N = notifications();
  if (!N || !Device.isDevice) return 'unavailable';
  try {
    const current = await N.getPermissionsAsync();
    if (current.granted) return 'granted';
    const asked = await N.requestPermissionsAsync();
    return asked.granted ? 'granted' : 'denied';
  } catch {
    return 'unavailable';
  }
}

// Returns the Expo push token, or null when push is unavailable or not permitted.
export async function getExpoPushToken(): Promise<string | null> {
  const N = notifications();
  if (!N || !Device.isDevice) return null;
  const projectId =
    EAS_PROJECT_ID ??
    (Constants.expoConfig?.extra?.eas?.projectId as string | undefined) ??
    Constants.easConfig?.projectId;
  try {
    const token = await N.getExpoPushTokenAsync(projectId ? { projectId } : undefined);
    return token.data;
  } catch (err) {
    console.warn('Expo push token unavailable', err);
    return null;
  }
}

function alertIdFrom(data: unknown): string | null {
  if (data && typeof data === 'object' && 'alert_id' in data) {
    const id = (data as { alert_id: unknown }).alert_id;
    if (typeof id === 'string' || typeof id === 'number') return String(id);
  }
  return null;
}

// Calls `onOpen(alertId)` when the user taps a notification (also on cold start).
export function subscribeToNotificationTaps(onOpen: (alertId: string) => void): () => void {
  const N = notifications();
  if (!N) return () => undefined;
  try {
    const last = N.getLastNotificationResponse();
    const lastId = last ? alertIdFrom(last.notification.request.content.data) : null;
    if (lastId) {
      onOpen(lastId);
      N.clearLastNotificationResponse();
    }
  } catch {
    // Not supported on this platform version.
  }
  const subscription = N.addNotificationResponseReceivedListener((response) => {
    const id = alertIdFrom(response.notification.request.content.data);
    if (id) onOpen(id);
  });
  return () => subscription.remove();
}
