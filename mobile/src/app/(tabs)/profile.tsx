import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, type UserPatch } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { CROPS, LIVESTOCK, toggle } from '@/constants';
import { useI18n } from '@/i18n';
import { Button, Chip, ChipRow, errorText, Field, LoadingView, SectionTitle, ThresholdPicker, styles as ui } from '@/ui/components';
import { colors, spacing } from '@/ui/theme';

export default function ProfileScreen() {
  const { t } = useI18n();
  const { user, updateUser, signOut } = useAuth();
  const [name, setName] = useState(user?.name ?? '');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => setName(user?.name ?? ''), [user?.name]);

  if (!user) return <LoadingView />;

  async function patch(change: UserPatch) {
    try {
      await updateUser(change);
    } catch (err) {
      Alert.alert(errorText(t, err));
    }
  }

  function saveName() {
    const value = name.trim();
    if (value !== (user?.name ?? '')) patch({ name: value || null });
  }

  function confirmDelete() {
    Alert.alert(t('profile.deleteTitle'), t('profile.deleteBody'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: async () => {
          setDeleting(true);
          try {
            await api.deleteMe();
            await signOut();
          } catch (err) {
            setDeleting(false);
            Alert.alert(errorText(t, err));
          }
        },
      },
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Field label={t('profile.name')} value={name} onChangeText={setName} onEndEditing={saveName} returnKeyType="done" />

      <View style={styles.item}>
        <Text style={ui.label}>{t('profile.email')}</Text>
        <Text style={ui.body}>{user.email}</Text>
      </View>

      <View style={styles.item}>
        <Text style={ui.label}>{t('profile.notificationEmail')}</Text>
        <View style={styles.inline}>
          <Text style={[ui.body, { flex: 1 }]}>{user.notification_email}</Text>
          <Pressable accessibilityRole="button" onPress={() => router.push('/change-email')} hitSlop={8}>
            <Text style={styles.link}>{t('profile.changeEmail')}</Text>
          </Pressable>
        </View>
      </View>

      <SectionTitle>{t('profile.language')}</SectionTitle>
      <ChipRow>
        <Chip label={t('language.es')} selected={user.language === 'es'} onPress={() => patch({ language: 'es' })} />
        <Chip label={t('language.en')} selected={user.language === 'en'} onPress={() => patch({ language: 'en' })} />
      </ChipRow>

      <SectionTitle>{t('profile.profileType')}</SectionTitle>
      <ChipRow>
        <Chip label={t('onboarding.producer')} selected={user.profile === 'producer'} onPress={() => patch({ profile: 'producer' })} />
        <Chip label={t('onboarding.resident')} selected={user.profile === 'resident'} onPress={() => patch({ profile: 'resident' })} />
      </ChipRow>

      <SectionTitle>{t('onboarding.cropsLabel')}</SectionTitle>
      <ChipRow>
        {CROPS.map((c) => (
          <Chip key={c} label={t(`crop.${c}`)} selected={user.crops.includes(c)} onPress={() => patch({ crops: toggle(user.crops, c) })} />
        ))}
      </ChipRow>

      <SectionTitle>{t('onboarding.livestockLabel')}</SectionTitle>
      <ChipRow>
        {LIVESTOCK.map((l) => (
          <Chip
            key={l}
            label={t(`livestock.${l}`)}
            selected={user.livestock.includes(l)}
            onPress={() => patch({ livestock: toggle(user.livestock, l) })}
          />
        ))}
      </ChipRow>

      <SectionTitle>{t('profile.defaultThreshold')}</SectionTitle>
      <ThresholdPicker value={user.default_threshold} onChange={(v) => patch({ default_threshold: v })} />

      <View style={styles.footer}>
        <Button label={t('profile.signOut')} variant="secondary" onPress={signOut} />
        <Button label={t('profile.deleteData')} variant="danger" onPress={confirmDelete} loading={deleting} />
        <Text style={ui.small}>{t('common.reanalysisNote')}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.xl, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  item: { gap: spacing.xs },
  inline: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  link: { color: colors.primary, fontWeight: '600' },
  footer: { gap: spacing.md, marginTop: spacing.xl },
});
