// Search bar with a dropdown of places. Coverage cells are searched locally first (no
// network); other places come from Photon, with Nominatim as a fallback (src/geo/search.ts).
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Keyboard, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { CoverageResponse } from '@/api/client';
import { centroid, fromPolygon, pointInCoverage } from '@/geo';
import {
  DEBOUNCE_MS,
  debounce,
  localSearch,
  mergeResults,
  nominatimProvider,
  photonProvider,
  PlaceSearcher,
  SearchUnavailableError,
  shouldSearch,
  type Place,
  type PlaceResult,
} from '@/geo/search';
import { useI18n } from '@/i18n';
import { haptic } from './feedback';
import { Icon } from './icons';
import { colors, radius, spacing } from './theme';

// Nominatim asks native apps for a descriptive User-Agent; browsers send their own.
const HEADERS: Record<string, string> =
  Platform.OS === 'web' ? {} : { 'User-Agent': 'FrostWatchAltiplano/1.0 (hackathon demo)' };

let searcher: PlaceSearcher | null = null;
function getSearcher(): PlaceSearcher {
  searcher ??= new PlaceSearcher([photonProvider(fetch, HEADERS), nominatimProvider(fetch, HEADERS)]);
  return searcher;
}

type Status = 'idle' | 'loading' | 'empty' | 'offline';

export function MapSearch({
  coverage,
  allowOutside,
  onSelect,
}: {
  coverage?: CoverageResponse;
  // On the Map tab outside places still move the camera; on the draw screen they cannot.
  allowOutside: boolean;
  onSelect: (place: PlaceResult) => void;
}) {
  const { t, language } = useI18n();
  const lang = language === 'en' ? 'en' : 'es';
  const [text, setText] = useState('');
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [status, setStatus] = useState<Status>('idle');
  const [open, setOpen] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const cells = useMemo<Place[]>(
    () =>
      coverage?.features.map((f) => ({
        id: `cell:${f.properties.point_id}`,
        name: f.properties.name,
        detail: t('search.coveredCell'),
        ...centroid(fromPolygon(f.geometry)),
        source: 'local' as const,
      })) ?? [],
    [coverage, t],
  );
  const isCovered = useMemo(
    () => (p: Place) => (coverage ? pointInCoverage({ latitude: p.latitude, longitude: p.longitude }, coverage) : false),
    [coverage],
  );

  const remote = useMemo(
    () =>
      debounce(async (query: string, local: Place[]) => {
        controller.current?.abort();
        const own = new AbortController();
        controller.current = own;
        try {
          const places = await getSearcher().search(query, { lang, signal: own.signal });
          if (own.signal.aborted) return;
          const merged = mergeResults(local, places, isCovered);
          setResults(merged);
          setStatus(merged.length ? 'idle' : 'empty');
        } catch (err) {
          if (own.signal.aborted) return;
          setStatus(err instanceof SearchUnavailableError ? 'offline' : 'idle');
        }
      }, DEBOUNCE_MS),
    [lang, isCovered],
  );

  useEffect(
    () => () => {
      remote.cancel();
      controller.current?.abort();
    },
    [remote],
  );

  function change(value: string) {
    setText(value);
    setOpen(true);
    const local = localSearch(value, cells);
    setResults(mergeResults(local, [], isCovered));
    if (!shouldSearch(value)) {
      remote.cancel();
      controller.current?.abort();
      setStatus('idle');
      return;
    }
    const cached = getSearcher().cached(value, lang);
    if (cached) {
      remote.cancel();
      const merged = mergeResults(local, cached, isCovered);
      setResults(merged);
      setStatus(merged.length ? 'idle' : 'empty');
      return;
    }
    setStatus('loading');
    remote.call(value, local);
  }

  function clear() {
    remote.cancel();
    controller.current?.abort();
    setText('');
    setResults([]);
    setStatus('idle');
    setOpen(false);
  }

  function choose(place: PlaceResult) {
    haptic.select();
    Keyboard.dismiss();
    setText(place.name);
    setOpen(false);
    onSelect(place);
  }

  const showList = open && text.length > 0 && (results.length > 0 || status === 'empty' || status === 'offline');

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <Icon name="search" size={20} color={colors.muted} />
        <TextInput
          value={text}
          onChangeText={change}
          onFocus={() => setOpen(true)}
          placeholder={t('search.placeholder')}
          placeholderTextColor={colors.muted}
          style={styles.input}
          returnKeyType="search"
          autoCorrect={false}
          accessibilityLabel={t('search.placeholder')}
        />
        {status === 'loading' ? <ActivityIndicator color={colors.primary} /> : null}
        {text ? (
          <Pressable accessibilityRole="button" accessibilityLabel={t('search.clear')} onPress={clear} hitSlop={10}>
            <Icon name="close" size={20} color={colors.muted} />
          </Pressable>
        ) : null}
      </View>
      {showList ? (
        <View style={styles.list}>
          {results.map((r) => {
            const blocked = !r.inCoverage && !allowOutside;
            return (
              <Pressable
                key={r.id}
                accessibilityRole="button"
                accessibilityState={{ disabled: blocked }}
                disabled={blocked}
                onPress={() => choose(r)}
                style={({ pressed }) => [styles.row, !r.inCoverage && styles.rowOutside, pressed && { opacity: 0.7 }]}
              >
                <Icon name={r.source === 'local' ? 'snowflake' : 'pin'} size={22} color={r.inCoverage ? colors.primary : colors.outsideText} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.name, !r.inCoverage && { color: colors.outsideText }]} numberOfLines={1}>
                    {r.name}
                  </Text>
                  {r.detail ? (
                    <Text style={styles.detail} numberOfLines={1}>
                      {r.detail}
                    </Text>
                  ) : null}
                  {!r.inCoverage ? <Text style={styles.outside}>{t('search.outside')}</Text> : null}
                </View>
              </Pressable>
            );
          })}
          {status === 'empty' && results.length === 0 ? <Text style={styles.message}>{t('search.noResults')}</Text> : null}
          {status === 'offline' ? <Text style={styles.message}>{t('search.offline')}</Text> : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { zIndex: 10 },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    minHeight: 50,
    shadowColor: colors.mapShadow,
    shadowOpacity: 1,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  input: { flex: 1, fontSize: 16, color: colors.text, paddingVertical: 10 },
  list: {
    marginTop: spacing.xs,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
    elevation: 5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 56,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowOutside: { opacity: 0.75 },
  name: { color: colors.text, fontSize: 16, fontWeight: '600' },
  detail: { color: colors.muted, fontSize: 13 },
  outside: { color: colors.outsideText, fontSize: 12, fontStyle: 'italic' },
  message: { color: colors.muted, fontSize: 14, padding: spacing.md, textAlign: 'center' },
});
