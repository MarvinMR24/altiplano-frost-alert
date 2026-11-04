import { useMemo, useState } from 'react';
import { FlatList, Modal, Pressable, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { itemMatches, labelFor, type CatalogItem, type Language } from '@/catalog/catalog';
import { useI18n, type TranslationKey } from '@/i18n';
import { Button, EmptyView, styles as ui } from '@/ui/components';
import { Icon, type IconName } from '@/ui/icons';
import { colors, spacing } from '@/ui/theme';

const CATEGORY_ORDER = ['tuber', 'grain', 'legume', 'vegetable', 'forage', 'greenhouse', 'livestock'] as const;

type Category = (typeof CATEGORY_ORDER)[number];

const CATEGORY_LABEL: Record<Category, TranslationKey> = {
  tuber: 'category.tuber',
  grain: 'category.grain',
  legume: 'category.legume',
  vegetable: 'category.vegetable',
  forage: 'category.forage',
  greenhouse: 'category.greenhouse',
  livestock: 'profile.livestock',
};

export function CatalogPicker({
  title,
  catalog,
  selected,
  onChange,
  maxSelected = 20,
  placeholder,
}: {
  title: string;
  catalog: CatalogItem[];
  selected: string[];
  onChange: (ids: string[]) => void;
  maxSelected?: number;
  placeholder: string;
}) {
  const { t, language } = useI18n();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const byId = useMemo(() => new Map(catalog.map((c) => [c.id, c])), [catalog]);
  const selectedItems = selected.map((id) => byId.get(id)).filter((c): c is CatalogItem => !!c);
  const unknownIds = selected.filter((id) => !byId.has(id));

  const groups = useMemo(() => {
    const matches = catalog.filter((c) => itemMatches(c, query, language as Language));
    const out: { category: Category; items: CatalogItem[] }[] = [];
    for (const category of CATEGORY_ORDER) {
      const items = matches.filter((c) => c.category === category);
      if (items.length > 0) out.push({ category, items });
    }
    return out;
  }, [catalog, query, language]);

  const rows = useMemo(() => {
    const list: ({ header: Category } | { item: CatalogItem })[] = [];
    for (const group of groups) {
      list.push({ header: group.category });
      for (const item of group.items) list.push({ item });
    }
    return list;
  }, [groups]);

  function toggle(id: string) {
    if (selected.includes(id)) onChange(selected.filter((s) => s !== id));
    else if (selected.length < maxSelected) onChange([...selected, id]);
  }

  const body = (
    <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
      <View style={styles.sheetHeader}>
        <Text style={ui.title}>{title}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('common.close')}
          onPress={() => setOpen(false)}
          hitSlop={8}
          style={({ pressed }) => [pressed && { opacity: 0.7 }]}
        >
          <Icon name="close" size={24} color={colors.text} />
        </Pressable>
      </View>
      <View style={styles.searchWrap}>
        <Icon name="search" size={20} color={colors.muted} />
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder={placeholder}
          placeholderTextColor={colors.muted}
          style={styles.searchInput}
          returnKeyType="search"
          accessibilityLabel={placeholder}
        />
        {query ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('common.close')}
            onPress={() => setQuery('')}
            hitSlop={8}
            style={({ pressed }) => [pressed && { opacity: 0.7 }]}
          >
            <Icon name="close" size={18} color={colors.muted} />
          </Pressable>
        ) : null}
      </View>
      {selected.length >= maxSelected ? (
        <Text style={ui.small}>{t('picker.maxReached', { n: maxSelected })}</Text>
      ) : null}
      <FlatList
        data={rows}
        keyExtractor={(row, i) => ('header' in row ? `h-${row.header}` : `r-${row.item.id}-${i}`)}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={<EmptyView message={t('picker.noResults')} icon="search" />}
        renderItem={({ item: row }) => {
          if ('header' in row) {
            return (
              <View style={styles.groupHeader}>
                <Icon name={row.header === 'livestock' ? 'llama' : (row.header as IconName)} size={18} color={colors.primary} />
                <Text style={ui.bodyStrong}>{t(CATEGORY_LABEL[row.header])}</Text>
              </View>
            );
          }
          const item = row.item;
          const isSelected = selected.includes(item.id);
          return (
            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{ checked: isSelected }}
              accessibilityLabel={labelFor(item, language as Language)}
              onPress={() => toggle(item.id)}
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
            >
              <Icon name={item.icon as IconName} size={24} color={colors.primary} />
              <Text style={[ui.body, { flex: 1 }]}>{labelFor(item, language as Language)}</Text>
              {isSelected ? <Icon name="check" size={20} color={colors.teal} /> : null}
            </Pressable>
          );
        }}
      />
      <Button label={t('common.done')} size="large" onPress={() => setOpen(false)} />
    </View>
  );

  return (
    <View style={{ gap: spacing.sm }}>
      <View style={styles.chips}>
        {selectedItems.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={t('picker.remove', { label: labelFor(item, language as Language) })}
            onPress={() => toggle(item.id)}
            style={({ pressed }) => [styles.chip, pressed && { opacity: 0.7 }]}
          >
            <Icon name={item.icon as IconName} size={16} color={colors.primaryText} />
            <Text style={styles.chipText}>{labelFor(item, language as Language)}</Text>
            <Icon name="close" size={14} color={colors.primaryText} />
          </Pressable>
        ))}
        {unknownIds.map((id) => (
          <Pressable
            key={id}
            accessibilityRole="button"
            accessibilityLabel={t('picker.remove', { label: id })}
            onPress={() => toggle(id)}
            style={({ pressed }) => [styles.chip, styles.chipUnknown, pressed && { opacity: 0.7 }]}
          >
            <Text style={styles.chipText}>{id}</Text>
            <Icon name="close" size={14} color={colors.primaryText} />
          </Pressable>
        ))}
        <Pressable
          accessibilityRole="button"
          onPress={() => setOpen(true)}
          style={({ pressed }) => [styles.chip, styles.chipAdd, pressed && { opacity: 0.7 }]}
        >
          <Icon name="plus" size={16} color={colors.primary} />
          <Text style={styles.chipAddText}>{title}</Text>
        </Pressable>
      </View>
      {width >= 700 && open ? (
        <View style={styles.inline}>{body}</View>
      ) : (
        <Modal visible={open} animationType="slide" onRequestClose={() => setOpen(false)}>
          <View style={[styles.modal, { paddingTop: insets.top }]}>{body}</View>
        </Modal>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.primary,
    borderRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: 44,
  },
  chipText: { color: colors.primaryText, fontWeight: '600' },
  chipUnknown: { backgroundColor: colors.muted },
  chipAdd: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primary },
  chipAddText: { color: colors.primary, fontWeight: '600' },
  modal: { flex: 1, backgroundColor: colors.background },
  inline: { borderWidth: 1, borderColor: colors.border, borderRadius: 16, backgroundColor: colors.background },
  sheet: { flex: 1, gap: spacing.md, padding: spacing.lg },
  sheetHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.surface,
    minHeight: 48,
  },
  searchInput: { flex: 1, fontSize: 16, color: colors.text, paddingVertical: 10 },
  groupHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingTop: spacing.md, paddingBottom: spacing.xs },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, minHeight: 48, paddingVertical: spacing.xs },
});
