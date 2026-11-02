import { router } from 'expo-router';
import { Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';

import { api, type Aoi } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import { Button, EmptyView, ErrorView, errorText, LevelBadge, LoadingView, styles as ui } from '@/ui/components';
import { colors, spacing } from '@/ui/theme';

export default function ZonesScreen() {
  const { t } = useI18n();
  const aois = useAsync(() => api.listAois(), [], { refetchOnFocus: true });

  function confirmDelete(aoi: Aoi) {
    Alert.alert(t('zones.deleteTitle'), t('zones.deleteBody', { name: aoi.name }), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: async () => {
          try {
            await api.deleteAoi(aoi.id);
            aois.setData((aois.data ?? []).filter((a) => a.id !== aoi.id));
          } catch (err) {
            Alert.alert(errorText(t, err));
          }
        },
      },
    ]);
  }

  let content;
  if (aois.loading && !aois.data) content = <LoadingView />;
  else if (aois.error && !aois.data) content = <ErrorView error={aois.error} onRetry={aois.reload} />;
  else if (!aois.data?.length) content = <EmptyView message={t('zones.empty')} />;
  else
    content = (
      <FlatList
        data={aois.data}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        refreshing={aois.loading}
        onRefresh={aois.reload}
        renderItem={({ item }) => <ZoneRow aoi={item} onDelete={() => confirmDelete(item)} />}
      />
    );

  return (
    <View style={{ flex: 1 }}>
      <View style={{ flex: 1 }}>{content}</View>
      <View style={styles.footer}>
        <Button label={t('zones.add')} onPress={() => router.push('/zones/draw')} />
      </View>
    </View>
  );
}

function ZoneRow({ aoi, onDelete }: { aoi: Aoi; onDelete: () => void }) {
  const { t, formatDate } = useI18n();
  const channels = [aoi.channels.push && t('zones.push'), aoi.channels.email && t('zones.email')].filter(Boolean);
  return (
    <View style={styles.row}>
      <View style={{ flex: 1, gap: spacing.xs }}>
        <Text style={ui.bodyStrong}>{aoi.name}</Text>
        {aoi.current ? (
          <>
            <LevelBadge level={aoi.current.level} probability={aoi.current.probability} />
            <Text style={ui.small}>
              {t('common.night', { date: formatDate(aoi.current.night_date) })} · {t('common.reanalysis')}
            </Text>
            <Text style={ui.small}>{t('zones.cellUsed', { cell: aoi.current.cell_used, km: aoi.current.distance_km })}</Text>
          </>
        ) : (
          <Text style={ui.small}>{t('zones.noCurrent')}</Text>
        )}
        <Text style={ui.small}>
          {t('zones.threshold', { n: aoi.threshold })} · {t('zones.channels')}: {channels.length ? channels.join(', ') : t('zones.none')}
        </Text>
      </View>
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={() => router.push(`/zones/${aoi.id}`)} hitSlop={8}>
          <Text style={styles.link}>{t('common.edit')}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={onDelete} hitSlop={8}>
          <Text style={[styles.link, { color: colors.danger }]}>{t('common.delete')}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.lg,
    gap: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  actions: { justifyContent: 'space-between', alignItems: 'flex-end' },
  link: { color: colors.primary, fontWeight: '600' },
  footer: {
    padding: spacing.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
  },
});
