// Livestock of the Altiplano. Old ids (llama, alpaca, sheep, cattle) are kept.
// No vicuña: wild, protected species.
import type { CatalogItem } from './catalog';

export const LIVESTOCK: CatalogItem[] = [
  { id: 'llama', category: 'livestock', labels: { es: 'Llama', en: 'Llama', ay: 'Qarwa', qu: 'Llama' }, synonyms: ['qarwa', 'llamo'], icon: 'llama' },
  { id: 'alpaca', category: 'livestock', labels: { es: 'Alpaca', en: 'Alpaca', ay: 'Allpaqa', qu: 'Alpaka' }, synonyms: [], icon: 'alpaca' },
  { id: 'sheep', category: 'livestock', labels: { es: 'Oveja', en: 'Sheep', ay: 'Iwija', qu: 'Uwiha' }, synonyms: ['ovejas', 'cordero'], icon: 'sheep' },
  { id: 'cattle', category: 'livestock', labels: { es: 'Ganado bovino', en: 'Cattle', ay: 'Waka', qu: 'Waka' }, synonyms: ['vaca', 'vacas', 'toro', 'bovino'], icon: 'cow' },
  { id: 'dairy_cattle', category: 'livestock', labels: { es: 'Ganado lechero', en: 'Dairy cattle' }, synonyms: ['lechero', 'vaca lechera'], icon: 'cow' },
  { id: 'goat', category: 'livestock', labels: { es: 'Cabra', en: 'Goat' }, synonyms: ['cabrío', 'chivo'], icon: 'sheep' },
  { id: 'pig', category: 'livestock', labels: { es: 'Cerdo', en: 'Pig', ay: 'Khuchi', qu: 'Khuchi' }, synonyms: ['chancho', 'puerco', 'khuchi'], icon: 'pig' },
  { id: 'chicken', category: 'livestock', labels: { es: 'Gallina', en: 'Chicken', ay: 'Wallpa', qu: 'Wallpa' }, synonyms: ['pollo', 'gallo', 'wallpa'], icon: 'chicken' },
  { id: 'guinea_pig', category: 'livestock', labels: { es: 'Cuy', en: 'Guinea pig', ay: "Wank'u", qu: 'Quwi' }, synonyms: ['cuyes', 'conejillo'], icon: 'guinea-pig' },
  { id: 'trout', category: 'livestock', labels: { es: 'Trucha', en: 'Trout farming' }, synonyms: ['truchas', 'piscicultura'], icon: 'fish' },
  { id: 'bees', category: 'livestock', labels: { es: 'Abejas', en: 'Bees' }, synonyms: ['abeja', 'apicultura', 'miel'], icon: 'bee' },
  { id: 'horse', category: 'livestock', labels: { es: 'Caballo', en: 'Horse', ay: 'Kawallu', qu: 'Kawallu' }, synonyms: ['yegua'], icon: 'horse' },
  { id: 'donkey', category: 'livestock', labels: { es: 'Burro', en: 'Donkey', ay: 'Asnu', qu: 'Asnu' }, synonyms: ['asno'], icon: 'horse' },
  { id: 'rabbit', category: 'livestock', labels: { es: 'Conejo', en: 'Rabbit' }, synonyms: ['conejos'], icon: 'guinea-pig' },
];

export const LIVESTOCK_BY_ID = new Map(LIVESTOCK.map((l) => [l.id, l]));
