import { useLocalSearchParams } from 'expo-router';
import { useEffect } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, type Metrics, type ModelCard } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import {
  Card,
  ConditionsList,
  DriversList,
  ErrorView,
  LevelBadge,
  LoadingView,
  ReanalysisNote,
  ReliabilityText,
  SectionTitle,
  styles as ui,
} from '@/ui/components';
import { spacing } from '@/ui/theme';

const METRIC_KEYS: (keyof Metrics)[] = [
  'pr_auc', 'f2', 'precision', 'recall', 'f1', 'roc_auc', 'brier', 'accuracy', 'majority_accuracy',
];

export default function AlertDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useI18n();
  const detail = useAsync(() => Promise.all([api.getAlert(id), api.getModelCard()]), [id]);
  const alert = detail.data?.[0];
  const card = detail.data?.[1];

  useEffect(() => {
    if (alert && !alert.read) api.markAlertRead(alert.id).catch(() => undefined);
  }, [alert]);

  if (detail.loading && !detail.data) return <LoadingView />;
  if (detail.error || !alert || !card) return <ErrorView error={detail.error} onRetry={detail.reload} />;

  const channels = alert.channels_sent.map((c) => t(c === 'push' ? 'zones.push' : 'zones.email')).join(', ');

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={ui.title}>{alert.explanation.headline}</Text>
      <Text style={ui.small}>{alert.aoi_name}</Text>
      <ReanalysisNote nightDate={alert.night_date} />
      <LevelBadge level={alert.level} probability={alert.probability} />
      {channels ? <Text style={ui.small}>{t('history.sentVia', { channels })}</Text> : null}

      <SectionTitle>{t('history.why')}</SectionTitle>
      <Text style={ui.body}>{alert.explanation.why}</Text>

      <SectionTitle>{t('history.actions')}</SectionTitle>
      <Bullets items={alert.explanation.actions} />

      <SectionTitle>{t('history.caveats')}</SectionTitle>
      <Bullets items={alert.explanation.caveats} />

      <SectionTitle>{t('map.conditions')}</SectionTitle>
      <ConditionsList conditions={alert.conditions_1800} />

      <SectionTitle>{t('map.drivers')}</SectionTitle>
      <DriversList drivers={alert.top_drivers} />

      <SectionTitle>{t('map.reliability')}</SectionTitle>
      <ReliabilityText reliability={alert.historical_reliability} />

      <SectionTitle>{t('history.outcome')}</SectionTitle>
      <Text style={ui.body}>
        {alert.outcome
          ? t(alert.outcome.frost ? 'map.frostObserved' : 'map.noFrostObserved', { t: alert.outcome.tmin_c })
          : t('history.outcomeUnknown')}
      </Text>

      <HowComputed summary={alert.model_card_summary} card={card} />
    </ScrollView>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <View style={{ gap: 2 }}>
      {items.map((item, i) => (
        <Text key={i} style={ui.body}>
          • {item}
        </Text>
      ))}
    </View>
  );
}

function HowComputed({ summary, card }: { summary: string; card: ModelCard }) {
  const { t } = useI18n();
  return (
    <Card style={{ marginTop: spacing.lg }}>
      <Text style={ui.bodyStrong}>{t('history.howComputed')}</Text>
      <Text style={ui.body}>{summary}</Text>
      <Text style={ui.small}>{t('map.modelVersion', { version: card.model_version })}</Text>
      <Text style={ui.small}>{t('history.trainedYears', { from: card.trained_years[0], to: card.trained_years[1] })}</Text>
      <Text style={ui.small}>{t('history.cells', { n: card.n_cells })}</Text>
      <View style={styles.metricsHeader}>
        <Text style={[ui.label, { flex: 2 }]} />
        <Text style={[ui.label, styles.metricCell]}>{t('history.validation')}</Text>
        <Text style={[ui.label, styles.metricCell]}>{t('history.test')}</Text>
      </View>
      {METRIC_KEYS.map((key) => (
        <View key={key} style={styles.metricsRow}>
          <Text style={[ui.small, { flex: 2 }]}>{t(`metric.${key}`)}</Text>
          <Text style={[ui.small, styles.metricCell]}>{fmt(card.metrics.validation[key])}</Text>
          <Text style={[ui.small, styles.metricCell]}>{fmt(card.metrics.test[key])}</Text>
        </View>
      ))}
      <Text style={[ui.label, { marginTop: spacing.sm }]}>{t('history.limitations')}</Text>
      <Bullets items={card.limitations} />
    </Card>
  );
}

function fmt(value: number | undefined): string {
  return typeof value === 'number' ? value.toFixed(3) : '-';
}

const styles = StyleSheet.create({
  container: { padding: spacing.xl, gap: spacing.sm, paddingBottom: spacing.xl * 2 },
  metricsHeader: { flexDirection: 'row', marginTop: spacing.sm },
  metricsRow: { flexDirection: 'row' },
  metricCell: { flex: 1, textAlign: 'right' },
});
