import { router } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useI18n } from '@/i18n';
import { AuthCard, LanguageChips, OrDivider, SocialButtons, useReduceMotion } from '@/ui/auth';
import { Button, styles as ui } from '@/ui/components';
import { Logo } from '@/ui/logo';
import { spacing } from '@/ui/theme';

export default function WelcomeScreen() {
  const { t } = useI18n();
  const reduceMotion = useReduceMotion();
  const logo = useRef(new Animated.Value(0)).current;
  const body = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (reduceMotion) {
      logo.setValue(1);
      body.setValue(1);
      return;
    }
    Animated.stagger(80, [
      Animated.timing(logo, { toValue: 1, duration: 350, useNativeDriver: true }),
      Animated.timing(body, { toValue: 1, duration: 350, useNativeDriver: true }),
    ]).start();
  }, [reduceMotion, logo, body]);

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <View style={styles.container}>
        <LanguageChips />
        <Animated.View
          style={{
            opacity: logo,
            transform: [{ translateY: logo.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }],
            alignItems: 'center',
            gap: spacing.sm,
          }}
        >
          <Logo size={120} />
          <Text style={ui.title}>{t('auth.title')}</Text>
          <Text style={[ui.muted, { textAlign: 'center' }]}>{t('welcome.tagline')}</Text>
        </Animated.View>
        <Animated.View style={{ opacity: body, gap: spacing.md }}>
          <AuthCard>
            <Button label={t('welcome.createAccount')} size="large" onPress={() => router.push('/signup')} />
            <Button label={t('welcome.signIn')} size="large" variant="secondary" onPress={() => router.push('/login')} />
            <OrDivider />
            <SocialButtons />
          </AuthCard>
          <Text style={[ui.small, { textAlign: 'center' }]}>{t('common.reanalysisNote')}</Text>
        </Animated.View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.xl, gap: spacing.xl, justifyContent: 'center' },
});
