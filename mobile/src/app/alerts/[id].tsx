import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Icon } from '@/ui/icons';

import { api, type Metrics, type ModelCard } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import {
  Card,
  ConditionsList,
  DriversList,
  EmptyView,
  ErrorView,
  ExplanationLabel,
  LoadingView,
  ReanalysisNote,
  ReplayTag,
  RiskMeter,
  SectionTitle,
  styles as ui,
} from '@/ui/components';
import { FadeIn } from '@/ui/motion';
import { TechnicalInfo } from '@/ui/TechnicalInfo';
import { SpeakButton } from '@/ui/SpeakButton';
import { colors, spacing } from '@/ui/theme';

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
  if (detail.error) return <ErrorView error={detail.error} onRetry={detail.reload} />;
  if (!alert || !card) return <EmptyView message={t('history.empty')} />;

  const channels = alert.channels_sent.map((c) => t(c === 'push' ? 'zones.push' : 'zones.email')).join(', ');
  const spoken = [
    alert.explanation.headline,
    alert.aoi_name,
    `${t('history.actions')}: ${alert.explanation.actions.join('. ')}`,
    `${t('history.why')}: ${alert.explanation.why}`,
  ].join('. ');

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {alert.mode === 'replay' ? <ReplayTag /> : null}
      <FadeIn>
        <Text style={ui.title}>{alert.explanation.headline}</Text>
      </FadeIn>
      <View style={styles.placeRow}>
        <Icon name="map" size={18} color={colors.muted} />
        <Text style={[ui.bodyStrong, { color: colors.muted }]}>{alert.aoi_name}</Text>
      </View>
      <FadeIn delay={80}>
        <RiskMeter level={alert.level} probability={alert.probability} />
      </FadeIn>
      <FadeIn delay={160}>
        <SpeakButton text={spoken} />
      </FadeIn>

      <FadeIn delay={220}>
        <View style={styles.actions}>
          <View style={styles.actionsHeader}>
            <Icon name="check-circle" size={24} color={colors.primary} />
            <Text style={styles.actionsTitle}>{t('history.actions')}</Text>
          </View>
          {alert.explanation.actions.map((item, i) => (
            <View key={i} style={styles.actionRow}>
              <View style={styles.actionNumber}>
                <Text style={styles.actionNumberText}>{i + 1}</Text>
              </View>
              <Text style={[ui.body, { flex: 1, fontSize: 17 }]}>{item}</Text>
            </View>
          ))}
        </View>
      </FadeIn>

      <SectionTitle>{t('history.why')}</SectionTitle>
      <Text style={ui.body}>{alert.explanation.why}</Text>

      <ReanalysisNote nightDate={alert.night_date} />
      <ExplanationLabel source={alert.explanation_source} />
      {channels ? <Text style={ui.small}>{t('history.sentVia', { channels })}</Text> : null}

      <SectionTitle>{t('history.outcome')}</SectionTitle>
      <Text style={ui.body}>
        {alert.outcome
          ? t(alert.outcome.frost ? 'map.frostObserved' : 'map.noFrostObserved', { t: alert.outcome.tmin_c })
          : t('history.outcomeUnknown')}
      </Text>

      <SectionTitle>{t('history.caveats')}</SectionTitle>
      <Bullets items={alert.explanation.caveats} />

      <TechnicalInfo>
        <SectionTitle>{t('map.conditions')}</SectionTitle>
        <ConditionsList conditions={alert.conditions_1800} />
        <SectionTitle>{t('map.drivers')}</SectionTitle>
        <DriversList drivers={alert.top_drivers} />
        <SectionTitle>{t('history.howComputed')}</SectionTitle>
        <ModelDetails summary={alert.model_card_summary} card={card} dataSource={alert.data_source} />
      </TechnicalInfo>
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

function ModelDetails({ summary, card, dataSource }: { summary: string; card: ModelCard; dataSource?: string }) {
  const { t } = useI18n();
  return (
    <View style={{ gap: spacing.sm }}>
      <Text style={ui.body}>{summary}</Text>
      <Text style={ui.small}>{t('map.modelVersion', { version: card.model_version })}</Text>
      <Text style={ui.small}>{t('history.trainedYears', { from: card.trained_years[0], to: card.trained_years[1] })}</Text>
      <Text style={ui.small}>{t('history.cells', { n: card.n_cells })}</Text>
      {dataSource ? <Text style={ui.small}>{dataSource}</Text> : null}
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
    </View>
  );
}

function fmt(value: number | undefined | null): string {
  return typeof value === 'number' ? value.toFixed(3) : '-';
}

const styles = StyleSheet.create({
  container: { padding: spacing.xl, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  placeRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  actions: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: colors.primary,
    padding: spacing.lg,
    gap: spacing.md,
  },
  actionsHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  actionsTitle: { color: colors.primary, fontSize: 19, fontWeight: '800' },
  actionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  actionNumber: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionNumberText: { color: colors.primaryText, fontWeight: '800', fontSize: 16 },
  howHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 44 },
  metricsHeader: { flexDirection: 'row', marginTop: spacing.sm },
  metricsRow: { flexDirection: 'row' },
  metricCell: { flex: 1, textAlign: 'right' },
});
