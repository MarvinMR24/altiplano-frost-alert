import { router } from 'expo-router';
import { useEffect, useState, type ReactNode } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, type UserPatch } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { CROPS } from '@/catalog/crops';
import { LIVESTOCK } from '@/catalog/livestock';
import { useI18n } from '@/i18n';
import { LanguageChips } from '@/ui/auth';
import { CatalogPicker } from '@/ui/CatalogPicker';
import { Button, Card, errorText, Field, LoadingView, SectionTitle, styles as ui } from '@/ui/components';
import { Icon, type IconName } from '@/ui/icons';
import { Logo } from '@/ui/logo';
import { ThresholdField } from '@/ui/ThresholdField';
import { colors, spacing } from '@/ui/theme';

export default function ProfileScreen() {
  const { t } = useI18n();
  const { user, updateUser, signOut } = useAuth();
  const insets = useSafeAreaInsets();
  const [name, setName] = useState(user?.name ?? '');
  const [editingName, setEditingName] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setName(user?.name ?? ''), [user?.name]);

  if (!user) return <LoadingView />;

  async function patch(change: UserPatch) {
    try {
      await updateUser(change);
    } catch (err) {
      setError(errorText(t, err));
    }
  }

  function saveName() {
    const value = name.trim();
    setEditingName(false);
    if (value !== (user?.name ?? '')) patch({ name: value || null });
  }

  async function deleteMe() {
    setDeleting(true);
    try {
      await api.deleteMe();
      await signOut();
    } catch (err) {
      setDeleting(false);
      setConfirmingDelete(false);
      setError(errorText(t, err));
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Logo size={56} />
        <View style={{ flex: 1 }}>
          <Text style={ui.title}>{user.name || t('profile.title')}</Text>
          <Text style={ui.muted}>{user.email}</Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('profile.editName')}
          onPress={() => setEditingName(!editingName)}
          hitSlop={8}
          style={({ pressed }) => [pressed && { opacity: 0.7 }]}
        >
          <Icon name="edit" size={22} color={colors.primary} />
        </Pressable>
      </View>
      {editingName ? (
        <Field
          label={t('profile.name')}
          icon="user"
          value={name}
          onChangeText={setName}
          onEndEditing={saveName}
          returnKeyType="done"
          maxLength={80}
          autoFocus
        />
      ) : null}

      <Section icon="globe" title={t('profile.language')}>
        <LanguageChips />
      </Section>

      <Section icon="profile" title={t('profile.profileType')}>
        <View style={styles.row2}>
          {(['producer', 'resident'] as const).map((p) => {
            const selected = user.profile === p;
            return (
              <Pressable
                key={p}
                accessibilityRole="radio"
                accessibilityState={{ selected }}
                onPress={() => patch({ profile: p })}
                style={({ pressed }) => [styles.pick, selected && styles.pickSelected, pressed && { opacity: 0.8 }]}
              >
                <Icon name={p} size={24} color={colors.primary} />
                <Text style={ui.bodyStrong}>{t(`onboarding.${p}`)}</Text>
              </Pressable>
            );
          })}
        </View>
      </Section>

      <Section icon="layers" title={t('profile.crops')}>
        <CatalogPicker
          title={t('profile.crops')}
          catalog={CROPS}
          selected={user.crops}
          onChange={(crops) => patch({ crops })}
          placeholder={t('picker.search')}
        />
      </Section>

      <Section icon="llama" title={t('profile.livestock')}>
        <CatalogPicker
          title={t('profile.livestock')}
          catalog={LIVESTOCK}
          selected={user.livestock}
          onChange={(livestock) => patch({ livestock })}
          placeholder={t('picker.search')}
        />
      </Section>

      <Section icon="bell" title={t('profile.alerts')}>
        <ThresholdField value={user.default_threshold} onChange={(v) => patch({ default_threshold: v })} />
        <View style={styles.item}>
          <Text style={ui.label}>{t('profile.notificationEmail')}</Text>
          <View style={styles.inline}>
            <Text style={[ui.body, { flex: 1 }]}>{user.notification_email}</Text>
            <Pressable accessibilityRole="button" onPress={() => router.push('/change-email')} hitSlop={8}>
              <Text style={styles.link}>{t('profile.changeEmail')}</Text>
            </Pressable>
          </View>
        </View>
      </Section>

      <Section icon="settings" title={t('profile.account')}>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/change-password')}
          style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.7 }]}
        >
          <Icon name="lock" size={20} color={colors.primary} />
          <Text style={[ui.body, { flex: 1 }]}>{t('profile.changePassword')}</Text>
          <Icon name="chevron-right" size={18} color={colors.muted} />
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={signOut}
          style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.7 }]}
        >
          <Icon name="logout" size={20} color={colors.primary} />
          <Text style={[ui.body, { flex: 1 }]}>{t('profile.signOut')}</Text>
          <Icon name="chevron-right" size={18} color={colors.muted} />
        </Pressable>
      </Section>

      <Section icon="alert" title={t('profile.dangerZone')} danger>
        <Button label={t('profile.deleteData')} variant="danger" onPress={() => setConfirmingDelete(true)} />
      </Section>

      {error ? <Text style={ui.errorText}>{error}</Text> : null}
      <Text style={ui.small}>{t('common.reanalysisNote')}</Text>
      <Text style={ui.small}>{t('profile.searchPrivacy')}</Text>

      <Modal visible={confirmingDelete} transparent animationType="slide" onRequestClose={() => setConfirmingDelete(false)}>
        <Pressable style={styles.backdrop} onPress={() => setConfirmingDelete(false)} accessibilityLabel={t('common.cancel')} />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
          <View style={styles.handle} />
          <Text style={ui.title}>{t('profile.deleteTitle')}</Text>
          <Text style={ui.body}>{t('profile.deleteBody')}</Text>
          <Button label={t('common.delete')} variant="danger" onPress={deleteMe} loading={deleting} />
          <Button label={t('common.cancel')} variant="secondary" onPress={() => setConfirmingDelete(false)} />
        </View>
      </Modal>
    </ScrollView>
  );
}

function Section({ icon, title, danger, children }: { icon: IconName; title: string; danger?: boolean; children: ReactNode }) {
  return (
    <View style={{ gap: spacing.sm }}>
      <SectionTitle>{title}</SectionTitle>
      <Card style={danger ? { borderColor: colors.danger } : undefined}>
        <View style={styles.sectionHead}>
          <Icon name={icon} size={22} color={danger ? colors.danger : colors.primary} />
          <Text style={[ui.bodyStrong, { flex: 1 }]}>{title}</Text>
        </View>
        {children}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.xl, gap: spacing.lg, paddingBottom: spacing.xl * 2 },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  row2: { flexDirection: 'row', gap: spacing.md },
  pick: {
    flex: 1,
    alignItems: 'center',
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: spacing.md,
    backgroundColor: colors.surface,
    minHeight: 88,
    justifyContent: 'center',
  },
  pickSelected: { borderColor: colors.primary, borderWidth: 2 },
  item: { gap: spacing.xs },
  inline: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  link: { color: colors.primary, fontWeight: '600' },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, minHeight: 48 },
  backdrop: { flex: 1, backgroundColor: colors.backdrop },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    gap: spacing.md,
  },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: spacing.sm },
});
