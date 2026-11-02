export const CROPS = ['potato', 'quinoa', 'barley', 'broad_bean', 'oca', 'alfalfa'] as const;
export const LIVESTOCK = ['llama', 'alpaca', 'sheep', 'cattle'] as const;

export type Crop = (typeof CROPS)[number];
export type Livestock = (typeof LIVESTOCK)[number];

export function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}
