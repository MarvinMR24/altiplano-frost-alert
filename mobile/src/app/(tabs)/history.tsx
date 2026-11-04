import { router } from 'expo-router';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';

import { api, type AlertSummary } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import { EmptyView, ErrorView, LevelBadge, LoadingView, ReplayTag, styles as ui } from '@/ui/components';
import { Icon } from '@/ui/icons';
import { FadeIn, stagger } from '@/ui/motion';
import { colors, levelColors, spacing } from '@/ui/theme';

export default function HistoryScreen() {
  const { t } = useI18n();
  const alerts = useAsync(() => api.listAlerts(), [], { refetchOnFocus: true });

  if (alerts.loading && !alerts.data) return <LoadingView />;
  if (alerts.error && !alerts.data) return <ErrorView error={alerts.error} onRetry={alerts.reload} />;
  if (!alerts.data?.length) return <EmptyView message={t('history.empty')} />;

  return (
    <FlatList
      data={alerts.data}
      keyExtractor={(a) => a.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
      refreshing={alerts.loading}
      onRefresh={alerts.reload}
      renderItem={({ item, index }) => (
        <FadeIn delay={stagger(index)}>
          <AlertRow alert={item} />
        </FadeIn>
      )}
    />
  );
}

function AlertRow({ alert }: { alert: AlertSummary }) {
  const { t, formatDate } = useI18n();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push(`/alerts/${alert.id}`)}
      style={({ pressed }) => [styles.row, { borderLeftColor: levelColors[alert.level] }, pressed && { opacity: 0.8 }]}
    >
      <View style={{ flex: 1, gap: spacing.xs }}>
        <View style={styles.titleRow}>
          {!alert.read ? <View style={styles.unreadDot} accessibilityLabel={t('history.unread')} /> : null}
          <Text style={[ui.bodyStrong, { flex: 1 }]} numberOfLines={2}>
            {alert.headline}
          </Text>
        </View>
        <Text style={ui.small}>
          {alert.aoi_name} · {t('common.night', { date: formatDate(alert.night_date) })} · {t('common.reanalysis')}
        </Text>
        <LevelBadge level={alert.level} probability={alert.probability} />
        {alert.mode === 'replay' ? <ReplayTag /> : null}
      </View>
      <Icon name="chevron-right" size={24} color={colors.muted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderLeftWidth: 6,
    padding: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  unreadDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.primary },
});
