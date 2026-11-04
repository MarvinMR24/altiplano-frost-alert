// Small motion kit built on React Native Animated (works in Expo Go and on the web).
// Every effect respects the system "reduce motion" setting and keeps content readable
// without motion: animations only add emphasis, they never carry information alone.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccessibilityInfo, Animated, Easing, Platform, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

// The native driver is not available on the web build.
export const NATIVE_DRIVER = Platform.OS !== 'web';

export function useReduceMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced).catch(() => undefined);
    const sub = AccessibilityInfo.addEventListener?.('reduceMotionChanged', setReduced);
    return () => sub?.remove();
  }, []);
  return reduced;
}

// Fades and lifts content in on mount. Use `delay` to stagger list items.
export function FadeIn({
  delay = 0,
  distance = 12,
  duration = 280,
  style,
  children,
}: {
  delay?: number;
  distance?: number;
  duration?: number;
  style?: StyleProp<ViewStyle>;
  children: ReactNode;
}) {
  const reduceMotion = useReduceMotion();
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) {
      progress.setValue(1);
      return;
    }
    const anim = Animated.timing(progress, {
      toValue: 1,
      duration,
      delay,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: NATIVE_DRIVER,
    });
    anim.start();
    return () => anim.stop();
  }, [reduceMotion, progress, delay, duration]);
  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [distance, 0] });
  return <Animated.View style={[style, { opacity: progress, transform: [{ translateY }] }]}>{children}</Animated.View>;
}

// Stagger delay for the item at `index`, capped so long lists do not wait.
export function stagger(index: number, step = 60, max = 8): number {
  return Math.min(index, max) * step;
}

// Springs content from small to full size, for success moments.
export function PopIn({ delay = 0, children }: { delay?: number; children: ReactNode }) {
  const reduceMotion = useReduceMotion();
  const scale = useRef(new Animated.Value(0.4)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) {
      scale.setValue(1);
      opacity.setValue(1);
      return;
    }
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, friction: 5, tension: 120, delay, useNativeDriver: NATIVE_DRIVER }),
      Animated.timing(opacity, { toValue: 1, duration: 180, delay, useNativeDriver: NATIVE_DRIVER }),
    ]).start();
  }, [reduceMotion, scale, opacity, delay]);
  return <Animated.View style={{ opacity, transform: [{ scale }] }}>{children}</Animated.View>;
}

// Expanding ring behind a marker or icon, to draw the eye to high risk.
export function PulseRing({ size, color, active = true }: { size: number; color: string; active?: boolean }) {
  const reduceMotion = useReduceMotion();
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!active || reduceMotion) return;
    const loop = Animated.loop(
      Animated.timing(progress, { toValue: 1, duration: 1600, easing: Easing.out(Easing.quad), useNativeDriver: NATIVE_DRIVER }),
    );
    loop.start();
    return () => loop.stop();
  }, [active, reduceMotion, progress]);
  if (!active || reduceMotion) return null;
  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [0.8, 1.7] });
  const opacity = progress.interpolate({ inputRange: [0, 1], outputRange: [0.55, 0] });
  return (
    <Animated.View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        { alignItems: 'center', justifyContent: 'center', opacity, transform: [{ scale }] },
      ]}
    >
      <View style={{ width: size, height: size, borderRadius: size / 2, borderWidth: 3, borderColor: color }} />
    </Animated.View>
  );
}

// Slow scale loop, for the loading logo.
export function Breathe({ children }: { children: ReactNode }) {
  const reduceMotion = useReduceMotion();
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(progress, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
        Animated.timing(progress, { toValue: 0, duration: 900, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE_DRIVER }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduceMotion, progress]);
  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [1, 1.07] });
  const opacity = progress.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1] });
  return <Animated.View style={{ opacity, transform: [{ scale }] }}>{children}</Animated.View>;
}

// Returns a translateX value that shakes whenever `trigger` changes to a truthy value.
export function useShake(trigger: unknown): Animated.Value {
  const reduceMotion = useReduceMotion();
  const offset = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!trigger || reduceMotion) return;
    offset.setValue(0);
    Animated.sequence(
      [8, -8, 6, -6, 3, 0].map((toValue) =>
        Animated.timing(offset, { toValue, duration: 45, useNativeDriver: NATIVE_DRIVER }),
      ),
    ).start();
  }, [trigger, reduceMotion, offset]);
  return offset;
}

// Fills from 0 to `fraction` (0 to 1) on mount and when the value changes.
export function useFill(fraction: number, delay = 0): Animated.Value {
  const reduceMotion = useReduceMotion();
  const fill = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) {
      fill.setValue(fraction);
      return;
    }
    // Width cannot use the native driver.
    Animated.timing(fill, { toValue: fraction, duration: 600, delay, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
  }, [fraction, delay, reduceMotion, fill]);
  return fill;
}
