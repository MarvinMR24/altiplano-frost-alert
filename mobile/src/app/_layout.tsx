import { router, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, type ReactNode } from 'react';
import { View } from 'react-native';
import { SafeAreaInsetsContext, SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { AuthProvider, useAuth } from '@/auth/AuthProvider';
import { USE_MOCK } from '@/config';
import { I18nProvider, useI18n } from '@/i18n';
import { configureForegroundHandler, subscribeToNotificationTaps } from '@/notifications/push';
import { LoadingView, MockBanner } from '@/ui/components';
import { colors } from '@/ui/theme';

configureForegroundHandler();

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <I18nProvider>
        <AuthProvider>
          <StatusBar style={USE_MOCK ? 'light' : 'dark'} />
          <RootNavigator />
        </AuthProvider>
      </I18nProvider>
    </SafeAreaProvider>
  );
}

// The mock banner takes the top safe area, so screens below it get a zero top inset.
function BelowBanner({ children }: { children: ReactNode }) {
  const insets = useSafeAreaInsets();
  if (!USE_MOCK) return <>{children}</>;
  return (
    <SafeAreaInsetsContext.Provider value={{ ...insets, top: 0 }}>{children}</SafeAreaInsetsContext.Provider>
  );
}

function RootNavigator() {
  const { status, user } = useAuth();
  const { t } = useI18n();
  const signedIn = status === 'signedIn' && !!user;
  const ready = signedIn && !!user?.onboarded;

  useEffect(() => {
    if (!ready) return;
    return subscribeToNotificationTaps((alertId) => router.push(`/alerts/${alertId}`));
  }, [ready]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <MockBanner />
      <BelowBanner>
        {status === 'loading' ? (
          <LoadingView />
        ) : (
          <Stack
            screenOptions={{
              contentStyle: { backgroundColor: colors.background },
              headerStyle: { backgroundColor: colors.headerBg },
              headerTintColor: colors.headerText,
              headerTitleStyle: { fontWeight: '700' },
            }}
          >
            <Stack.Protected guard={!signedIn}>
              <Stack.Screen name="welcome" options={{ headerShown: false }} />
              <Stack.Screen name="signup" options={{ headerShown: false }} />
              <Stack.Screen name="login" options={{ headerShown: false }} />
              <Stack.Screen name="verify" options={{ headerShown: false }} />
              <Stack.Screen name="forgot" options={{ headerShown: false }} />
            </Stack.Protected>
            {/* Signed out visitors land on Welcome (not on the first free screen the router picks). */}
            <Stack.Protected guard={signedIn && !user?.onboarded} redirectTo={signedIn ? '/' : '/welcome'}>
              <Stack.Screen name="onboarding" options={{ headerShown: false }} />
            </Stack.Protected>
            <Stack.Protected guard={ready} redirectTo={signedIn ? '/onboarding' : '/welcome'}>
              <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
              <Stack.Screen
                name="zones/draw"
                options={{ presentation: 'fullScreenModal', title: t('draw.title'), gestureEnabled: false }}
              />
              <Stack.Screen name="zones/[id]" options={{ title: t('draw.editTitle'), headerBackTitle: t('common.back') }} />
              <Stack.Screen name="alerts/[id]" options={{ title: '', headerBackTitle: t('common.back') }} />
              <Stack.Screen
                name="change-email"
                options={{ presentation: 'modal', title: t('profile.changeEmailTitle') }}
              />
              <Stack.Screen name="change-password" options={{ title: t('profile.changePasswordTitle') }} />
            </Stack.Protected>
          </Stack>
        )}
      </BelowBanner>
    </View>
  );
}
