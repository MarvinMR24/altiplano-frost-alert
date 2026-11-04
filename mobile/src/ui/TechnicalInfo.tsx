// "Technical information": a section at the bottom of a screen, closed by default, for the
// numbers most people do not need (drivers, conditions, model metrics).
import { useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useI18n } from '@/i18n';
import { haptic } from './feedback';
import { Icon } from './icons';
import { FadeIn } from './motion';
import { colors, radius, spacing } from './theme';

export function TechnicalInfo({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.box}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        onPress={() => {
          haptic.select();
          setOpen(!open);
        }}
        hitSlop={6}
        style={({ pressed }) => [styles.header, pressed && { opacity: 0.7 }]}
      >
        <Icon name="settings" size={20} color={colors.muted} />
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{t('tech.title')}</Text>
          {!open ? <Text style={styles.subtitle}>{t('tech.subtitle')}</Text> : null}
        </View>
        <Icon name={open ? 'chevron-down' : 'chevron-right'} size={20} color={colors.muted} />
      </Pressable>
      {open ? <FadeIn style={styles.body}>{children}</FadeIn> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    marginTop: spacing.xl,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, padding: spacing.md, minHeight: 52 },
  title: { color: colors.muted, fontSize: 15, fontWeight: '700' },
  subtitle: { color: colors.muted, fontSize: 12 },
  body: { paddingHorizontal: spacing.md, paddingBottom: spacing.md, gap: spacing.sm },
});
