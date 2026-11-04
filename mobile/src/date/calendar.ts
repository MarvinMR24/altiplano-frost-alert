// Pure calendar helpers for the night picker. Monday-first weeks. No dependencies,
// so the logic is unit tested with plain node (mobile/scripts/unit-tests.mjs).

export type Language = 'es' | 'en' | 'ay' | 'qu';

export interface DayCell {
  iso: string;
  day: number;
}

export type Week = (DayCell | null)[];

export function toIso(year: number, month: number, day: number): string {
  const m = String(month + 1).padStart(2, '0');
  const d = String(day).padStart(2, '0');
  return `${year}-${m}-${d}`;
}

// Weeks of one month. Cells outside the month are null. Weeks start on Monday.
export function monthGrid(year: number, month: number): Week[] {
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const firstWeekday = (new Date(Date.UTC(year, month, 1)).getUTCDay() + 6) % 7;
  const weeks: Week[] = [];
  let week: Week = new Array(firstWeekday).fill(null);
  for (let day = 1; day <= daysInMonth; day++) {
    week.push({ iso: toIso(year, month, day), day });
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }
  return weeks;
}

export function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const total = year * 12 + month + delta;
  return { year: Math.floor(total / 12), month: total % 12 };
}

const MONTHS_FALLBACK: Record<Language, string[]> = {
  es: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
  en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
  ay: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
  qu: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
};

const WEEKDAYS_FALLBACK: Record<Language, string[]> = {
  es: ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'],
  en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
  ay: ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'],
  qu: ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'],
};

const LOCALE: Record<Language, string> = { es: 'es-BO', en: 'en-US', ay: 'ay-BO', qu: 'qu-BO' };

export function monthName(language: Language, month: number): string {
  try {
    const name = new Intl.DateTimeFormat(LOCALE[language], { month: 'long', timeZone: 'UTC' }).format(
      new Date(Date.UTC(2024, month, 1)),
    );
    if (name && !/^\d+$/.test(name)) return name.charAt(0).toUpperCase() + name.slice(1);
  } catch {
    // Fall through to the table below.
  }
  return MONTHS_FALLBACK[language][month];
}

// Seven short weekday names starting on Monday.
export function weekdayNames(language: Language): string[] {
  try {
    const monday = Date.UTC(2024, 0, 1); // 2024-01-01 was a Monday.
    const names = Array.from({ length: 7 }, (_, i) =>
      new Intl.DateTimeFormat(LOCALE[language], { weekday: 'short', timeZone: 'UTC' }).format(
        new Date(monday + i * 86400000),
      ),
    );
    if (names.every((n) => n && !/^\d+$/.test(n))) return names;
  } catch {
    // Fall through to the table below.
  }
  return WEEKDAYS_FALLBACK[language];
}

export function yearsInRange(minIso: string, maxIso: string): number[] {
  const from = Number(minIso.slice(0, 4));
  const to = Number(maxIso.slice(0, 4));
  const years: number[] = [];
  for (let y = from; y <= to; y++) years.push(y);
  return years;
}
