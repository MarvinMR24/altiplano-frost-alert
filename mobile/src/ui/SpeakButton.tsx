// "Listen" button: reads a text aloud with the phone's voice (expo-speech), for people
// who prefer to hear the alert instead of reading it. Aymara and Quechua have no system
// voice, so those languages are read with the Spanish voice and the button says so.
import * as Speech from 'expo-speech';
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import type { Language } from '@/api/client';
import { useI18n } from '@/i18n';
import { haptic } from './feedback';
import { Icon } from './icons';
import { NATIVE_DRIVER, useReduceMotion } from './motion';
import { colors, radius, spacing } from './theme';

// Android's Google voice ships Latin American Spanish as es-US; iOS ships es-MX.
const SPANISH = Platform.OS === 'android' ? 'es-US' : 'es-MX';
const VOICE: Record<Language, string> = { es: SPANISH, en: 'en-US', ay: SPANISH, qu: SPANISH };

export function SpeakButton({ text }: { text: string }) {
  const { t, language } = useI18n();
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => () => void Speech.stop(), []);
  // A new text (other alert or place) stops the current reading.
  useEffect(() => {
    Speech.stop();
    setSpeaking(false);
  }, [text]);

  function toggle() {
    haptic.tap();
    if (speaking) {
      Speech.stop();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    Speech.speak(text, {
      language: VOICE[language],
      rate: 0.9,
      onDone: () => setSpeaking(false),
      onStopped: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    });
  }

  return (
    <View style={{ gap: spacing.xs }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={speaking ? t('common.stopListening') : t('common.listen')}
        onPress={toggle}
        style={({ pressed }) => [styles.button, speaking && styles.buttonOn, pressed && { opacity: 0.85 }]}
      >
        <Icon name={speaking ? 'stop' : 'speaker'} size={24} color={speaking ? colors.primaryText : colors.primary} />
        <Text style={[styles.text, speaking && styles.textOn]}>
          {speaking ? t('common.stopListening') : t('common.listen')}
        </Text>
        {speaking ? <SoundBars /> : null}
      </Pressable>
      {language === 'ay' || language === 'qu' ? <Text style={styles.note}>{t('speech.spanishVoice')}</Text> : null}
    </View>
  );
}

function SoundBars() {
  const reduceMotion = useReduceMotion();
  const bars = useRef([0, 1, 2].map(() => new Animated.Value(0.4))).current;
  useEffect(() => {
    if (reduceMotion) return;
    const loops = bars.map((bar, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(bar, { toValue: 1, duration: 260 + i * 70, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
          Animated.timing(bar, { toValue: 0.4, duration: 260 + i * 70, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
        ]),
      ),
    );
    loops.forEach((l) => l.start());
    return () => loops.forEach((l) => l.stop());
  }, [bars, reduceMotion]);
  return (
    <View style={styles.bars} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {bars.map((bar, i) => (
        <Animated.View key={i} style={[styles.bar, { transform: [{ scaleY: bar }] }]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    minHeight: 52,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
  },
  buttonOn: { backgroundColor: colors.primary },
  text: { color: colors.primary, fontSize: 17, fontWeight: '700' },
  textOn: { color: colors.primaryText },
  bars: { flexDirection: 'row', alignItems: 'center', gap: 3, height: 18 },
  bar: { width: 4, height: 18, borderRadius: 2, backgroundColor: colors.primaryText },
  note: { color: colors.muted, fontSize: 13, textAlign: 'center' },
});
