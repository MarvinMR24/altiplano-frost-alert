import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';

import { api, type Channels, type Threshold } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import {
  Button,
  EmptyView,
  ErrorView,
  errorText,
  Field,
  LoadingView,
  SectionTitle,
  ThresholdPicker,
  ToggleRow,
  styles as ui,
} from '@/ui/components';
import { spacing } from '@/ui/theme';

export default function EditZoneScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useI18n();
  // The contract has no GET /aois/{id}; the list is small.
  const aois = useAsync(() => api.listAois(), []);
  const aoi = aois.data?.find((a) => a.id === id);

  const [name, setName] = useState('');
  const [threshold, setThreshold] = useState<Threshold>(50);
  const [channels, setChannels] = useState<Channels>({ push: true, email: true });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!aoi) return;
    setName(aoi.name);
    setThreshold(aoi.threshold);
    setChannels(aoi.channels);
  }, [aoi]);

  if (aois.loading && !aois.data) return <LoadingView />;
  if (aois.error) return <ErrorView error={aois.error} onRetry={aois.reload} />;
  if (!aoi) return <EmptyView message={t('common.error')} />;

  async function save() {
    if (!name.trim()) {
      setError(t('draw.nameRequired'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateAoi(id, { name: name.trim(), threshold, channels });
      router.back();
    } catch (err) {
      setError(errorText(t, err));
      setSaving(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.form}>
      <Field label={t('draw.nameLabel')} value={name} onChangeText={setName} maxLength={60} />
      <SectionTitle>{t('draw.thresholdLabel')}</SectionTitle>
      <ThresholdPicker value={threshold} onChange={setThreshold} />
      <SectionTitle>{t('draw.channelsLabel')}</SectionTitle>
      <ToggleRow label={t('zones.push')} value={channels.push} onChange={(push) => setChannels({ ...channels, push })} />
      <ToggleRow label={t('zones.email')} value={channels.email} onChange={(email) => setChannels({ ...channels, email })} />
      {error ? <Text style={ui.errorText}>{error}</Text> : null}
      <Button label={t('common.save')} onPress={save} loading={saving} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  form: { padding: spacing.xl, gap: spacing.md },
});
