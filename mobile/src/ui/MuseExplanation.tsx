// Plain explanation of a place and night, written by Muse Spark when the user opens it:
// what happened that night, what came next, what to do and where to read more.
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';

import { api, type Language, type PlaceExplanation } from '@/api/client';
import { useAsync } from '@/hooks/useAsync';
import { LANGUAGES, useI18n } from '@/i18n';
import { haptic } from './feedback';
import { Button, styles as ui } from './components';
import { Icon } from './icons';
import { FadeIn, NATIVE_DRIVER, useReduceMotion } from './motion';
import { SpeakButton } from './SpeakButton';
import { colors, radius, spacing } from './theme';

export function speakableText(e: PlaceExplanation): string {
  return [e.headline, e.what_happened, e.what_next, ...e.actions].join('. ');
}

export function MuseExplanation({ pointId, nightDate }: { pointId: string; nightDate: string }) {
  const { t, language: appLanguage } = useI18n();
  // Language of the explanation. Picking another one first generates the text in that
  // language, shows it, and then reads it aloud.
  const [language, setLanguage] = useState<Language>(appLanguage);
  const [readAfterLoad, setReadAfterLoad] = useState(false);
  const [autoPlayKey, setAutoPlayKey] = useState<number | undefined>(undefined);
  const explanation = useAsync(() => api.getPlaceExplanation(pointId, nightDate, language), [pointId, nightDate, language]);
  const e = explanation.loading ? undefined : explanation.data;

  useEffect(() => {
    if (!readAfterLoad || !e) return;
    setReadAfterLoad(false);
    setAutoPlayKey((k) => (k ?? 0) + 1);
  }, [e, readAfterLoad]);

  function choose(next: Language) {
    haptic.select();
    setReadAfterLoad(true);
    if (next === language && e) setAutoPlayKey((k) => (k ?? 0) + 1);
    else setLanguage(next);
  }

  const chips = (
    <View style={{ gap: spacing.xs }}>
      <Text style={ui.label}>{t('muse.listenIn')}</Text>
      <View style={styles.chips}>
        {LANGUAGES.map((l) => {
          const on = l.id === language;
          return (
            <Pressable
              key={l.id}
              accessibilityRole="button"
              accessibilityState={{ selected: on }}
              accessibilityLabel={`${t('muse.listenIn')} ${t(l.labelKey)}`}
              onPress={() => choose(l.id)}
              style={({ pressed }) => [styles.chip, on && styles.chipOn, pressed && { opacity: 0.8 }]}
            >
              <Icon name="speaker" size={16} color={on ? colors.primaryText : colors.primary} />
              <Text style={[styles.chipText, on && styles.chipTextOn]}>{t(l.labelKey)}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );

  if (!e && !explanation.error) {
    return (
      <View style={{ gap: spacing.md }}>
        {chips}
        <Thinking />
      </View>
    );
  }
  if (explanation.error || !e) {
    return (
      <View style={{ gap: spacing.md }}>
        {chips}
        <View style={styles.card}>
          <Text style={ui.body}>{t('muse.error')}</Text>
          <Button label={t('common.retry')} variant="secondary" onPress={explanation.reload} />
        </View>
      </View>
    );
  }

  // Asked for another language but got the Spanish base (translation not available yet).
  const fellBack = language !== e.language;
  return (
    <FadeIn style={{ gap: spacing.md }}>
      {chips}
      <SpeakButton text={speakableText(e)} language={e.language} autoPlayKey={autoPlayKey} />
      <View style={styles.card}>
        <Text style={styles.headline}>{e.headline}</Text>
        <Section icon="moon-stars" title={t('muse.whatHappened')} text={e.what_happened} />
        <Section icon="sunrise" title={t('muse.whatNext')} text={e.what_next} />
        <View style={{ gap: spacing.sm }}>
          <View style={styles.sectionHead}>
            <Icon name="check-circle" size={20} color={colors.primary} />
            <Text style={styles.sectionTitle}>{t('muse.whatToDo')}</Text>
          </View>
          {e.actions.map((a, i) => (
            <View key={i} style={styles.actionRow}>
              <View style={styles.actionNumber}>
                <Text style={styles.actionNumberText}>{i + 1}</Text>
              </View>
              <Text style={[ui.body, { flex: 1 }]}>{a}</Text>
            </View>
          ))}
        </View>
        <View style={styles.byline}>
          <Icon name="info" size={14} color={colors.muted} />
          <Text style={[ui.small, { flex: 1 }]}>
            {e.source === 'muse' ? t('muse.byMuse') : t('muse.byTemplate')}
            {e.translated ? ` ${t('muse.translatedNote')}` : ''}
            {fellBack ? ` ${t('muse.spanishFallback')}` : ''}
          </Text>
        </View>
      </View>

      <View style={styles.card}>
        <View style={styles.sectionHead}>
          <Icon name="globe" size={20} color={colors.primary} />
          <Text style={styles.sectionTitle}>{t('muse.moreInfo')}</Text>
        </View>
        {e.sources.map((s) => (
          <Pressable
            key={s.url}
            accessibilityRole="link"
            accessibilityLabel={`${s.name}. ${s.why}`}
            onPress={() => WebBrowser.openBrowserAsync(s.url).catch(() => undefined)}
            style={({ pressed }) => [styles.source, pressed && { opacity: 0.7 }]}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.sourceName}>{s.name}</Text>
              <Text style={ui.small}>{s.why}</Text>
            </View>
            <Icon name="arrow-right" size={20} color={colors.primary} />
          </Pressable>
        ))}
      </View>
    </FadeIn>
  );
}

function Section({ icon, title, text }: { icon: 'moon-stars' | 'sunrise'; title: string; text: string }) {
  return (
    <View style={{ gap: spacing.xs }}>
      <View style={styles.sectionHead}>
        <Icon name={icon} size={20} color={colors.primary} />
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      <Text style={ui.body}>{text}</Text>
    </View>
  );
}

// Waiting state while Muse writes: three pulsing dots.
function Thinking() {
  const { t } = useI18n();
  const reduceMotion = useReduceMotion();
  const dots = useRef([0, 1, 2].map(() => new Animated.Value(0.3))).current;
  useEffect(() => {
    if (reduceMotion) return;
    const loops = dots.map((d, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 160),
          Animated.timing(d, { toValue: 1, duration: 320, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
          Animated.timing(d, { toValue: 0.3, duration: 320, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
        ]),
      ),
    );
    loops.forEach((l) => l.start());
    return () => loops.forEach((l) => l.stop());
  }, [dots, reduceMotion]);
  return (
    <View style={[styles.card, styles.thinking]} accessibilityRole="progressbar" accessibilityLabel={t('muse.thinking')}>
      <View style={styles.dots}>
        {dots.map((d, i) => (
          <Animated.View key={i} style={[styles.dot, { opacity: d }]} />
        ))}
      </View>
      <View style={{ flex: 1 }}>
        <Text style={ui.body}>{t('muse.thinking')}</Text>
        <Text style={ui.small}>{t('muse.thinkingSlow')}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.md,
  },
  thinking: { flexDirection: 'row', alignItems: 'center' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    minHeight: 44,
    paddingHorizontal: spacing.md,
    borderRadius: 22,
    borderWidth: 2,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
  },
  chipOn: { backgroundColor: colors.primary },
  chipText: { color: colors.primary, fontWeight: '700', fontSize: 15 },
  chipTextOn: { color: colors.primaryText },
  dots: { flexDirection: 'row', gap: 6 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
  headline: { color: colors.text, fontSize: 20, fontWeight: '800' },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  sectionTitle: { color: colors.primary, fontSize: 17, fontWeight: '800' },
  actionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  actionNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionNumberText: { color: colors.primaryText, fontWeight: '800', fontSize: 15 },
  byline: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.xs },
  source: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    minHeight: 56,
    paddingVertical: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  sourceName: { color: colors.primary, fontSize: 16, fontWeight: '700' },
});
