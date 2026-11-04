import { Tabs } from 'expo-router';
import type { ColorValue } from 'react-native';

import { useI18n } from '@/i18n';
import { Icon, type IconName } from '@/ui/icons';
import { colors } from '@/ui/theme';

function icon(name: IconName) {
  return ({ color, size }: { color: ColorValue; size: number }) => (
    <Icon name={name} color={typeof color === 'string' ? color : colors.tabInactive} size={size} />
  );
}

export default function TabsLayout() {
  const { t } = useI18n();
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.tabBg,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarStyle: { backgroundColor: colors.headerBg },
        tabBarActiveBackgroundColor: colors.navyLight,
        headerStyle: { backgroundColor: colors.headerBg },
        headerTintColor: colors.headerText,
        headerTitleStyle: { fontWeight: '700' },
        lazy: true,
      }}
    >
      <Tabs.Screen name="index" options={{ title: t('tabs.map'), headerShown: false, tabBarIcon: icon('map') }} />
      <Tabs.Screen name="zones" options={{ title: t('tabs.zones'), tabBarIcon: icon('layers') }} />
      <Tabs.Screen name="history" options={{ title: t('tabs.history'), tabBarIcon: icon('history') }} />
      <Tabs.Screen name="profile" options={{ title: t('tabs.profile'), tabBarIcon: icon('profile') }} />
    </Tabs>
  );
}
