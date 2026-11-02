import { router, Stack } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, Polygon, Polyline, type MapPressEvent, type Region } from 'react-native-maps';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, ApiError, type Channels, type Threshold } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { fromPolygon, polygonInsideCoverage, toPolygon, type LatLng } from '@/geo';
import { useAsync } from '@/hooks/useAsync';
import { useI18n } from '@/i18n';
import { Button, ErrorView, errorText, Field, LoadingView, SectionTitle, ThresholdPicker, ToggleRow, styles as ui } from '@/ui/components';
import { colors, spacing } from '@/ui/theme';

const MAX_VERTICES = 12;
const INITIAL_REGION: Region = { latitude: -17.4, longitude: -68.0, latitudeDelta: 2.2, longitudeDelta: 2.2 };

export default function DrawZoneScreen() {
  const { t } = useI18n();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const coverage = useAsync(() => api.getCoverage(), []);

  const [step, setStep] = useState<'draw' | 'form'>('draw');
  const [vertices, setVertices] = useState<LatLng[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [threshold, setThreshold] = useState<Threshold>(user?.default_threshold ?? 50);
  const [channels, setChannels] = useState<Channels>({ push: true, email: true });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function addVertex(e: MapPressEvent) {
    if (vertices.length >= MAX_VERTICES) {
      setNotice(t('draw.maxReached'));
      return;
    }
    setNotice(null);
    setVertices([...vertices, e.nativeEvent.coordinate]);
  }

  function finish() {
    if (!coverage.data || vertices.length < 3) return;
    if (!polygonInsideCoverage(vertices, coverage.data)) {
      setNotice(`${t('draw.outside')}. ${t('draw.outsideBody')}`);
      return;
    }
    setNotice(null);
    setStep('form');
  }

  async function save() {
    if (!name.trim()) {
      setFormError(t('draw.nameRequired'));
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await api.createAoi({ name: name.trim(), polygon: toPolygon(vertices), threshold, channels });
      router.back();
    } catch (err) {
      setFormError(err instanceof ApiError && err.status === 422 ? t('draw.outside') : errorText(t, err));
      setSaving(false);
    }
  }

  const header = (
    <Stack.Screen
      options={{
        title: step === 'draw' ? t('draw.title') : t('draw.formTitle'),
        headerLeft: () => (
          <Pressable onPress={() => (step === 'form' ? setStep('draw') : router.back())} hitSlop={8}>
            <Text style={styles.headerLink}>{step === 'form' ? t('common.back') : t('common.cancel')}</Text>
          </Pressable>
        ),
      }}
    />
  );

  if (coverage.loading && !coverage.data) return <>{header}<LoadingView /></>;
  if (coverage.error || !coverage.data) return <>{header}<ErrorView error={coverage.error} onRetry={coverage.reload} /></>;

  if (step === 'form') {
    return (
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        {header}
        <ScrollView contentContainerStyle={styles.form}>
          <Field
            label={t('draw.nameLabel')}
            placeholder={t('draw.namePlaceholder')}
            value={name}
            onChangeText={setName}
            maxLength={60}
            autoFocus
          />
          <SectionTitle>{t('draw.thresholdLabel')}</SectionTitle>
          <ThresholdPicker value={threshold} onChange={setThreshold} />
          <SectionTitle>{t('draw.channelsLabel')}</SectionTitle>
          <ToggleRow label={t('zones.push')} value={channels.push} onChange={(push) => setChannels({ ...channels, push })} />
          <ToggleRow label={t('zones.email')} value={channels.email} onChange={(email) => setChannels({ ...channels, email })} />
          {formError ? <Text style={ui.errorText}>{formError}</Text> : null}
          <Button label={t('draw.saveZone')} onPress={save} loading={saving} />
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      {header}
      <MapView style={{ flex: 1 }} initialRegion={INITIAL_REGION} onPress={addVertex}>
        {coverage.data.features.map((f) => (
          <Polygon
            key={f.properties.point_id}
            coordinates={fromPolygon(f.geometry)}
            fillColor={colors.coverageFill}
            strokeColor={colors.coverageStroke}
            strokeWidth={1}
            tappable={false}
          />
        ))}
        {vertices.length >= 3 ? (
          <Polygon coordinates={vertices} fillColor={colors.aoiFill} strokeColor={colors.aoiStroke} strokeWidth={2} />
        ) : vertices.length === 2 ? (
          <Polyline coordinates={vertices} strokeColor={colors.aoiStroke} strokeWidth={2} />
        ) : null}
        {vertices.map((v, i) => (
          <Marker key={`v-${i}`} coordinate={v} anchor={{ x: 0.5, y: 0.5 }}>
            <View style={styles.vertex} />
          </Marker>
        ))}
      </MapView>
      <View style={[styles.toolbar, { paddingBottom: insets.bottom + spacing.md }]}>
        <Text style={ui.body}>{t('draw.hint')}</Text>
        <Text style={ui.small}>{t('draw.vertices', { n: vertices.length })}</Text>
        {notice ? <Text style={ui.errorText}>{notice}</Text> : null}
        <View style={styles.buttons}>
          <Button
            label={t('draw.undo')}
            variant="secondary"
            disabled={!vertices.length}
            onPress={() => {
              setNotice(null);
              setVertices(vertices.slice(0, -1));
            }}
            style={{ flex: 1 }}
          />
          <Button
            label={t('draw.clear')}
            variant="secondary"
            disabled={!vertices.length}
            onPress={() => {
              setNotice(null);
              setVertices([]);
            }}
            style={{ flex: 1 }}
          />
          <Button label={t('draw.finish')} disabled={vertices.length < 3} onPress={finish} style={{ flex: 1 }} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  headerLink: { color: colors.primary, fontSize: 16 },
  vertex: { width: 14, height: 14, borderRadius: 7, backgroundColor: colors.aoiStroke, borderWidth: 2, borderColor: '#fff' },
  toolbar: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    gap: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  buttons: { flexDirection: 'row', gap: spacing.sm },
  form: { padding: spacing.xl, gap: spacing.md },
});
