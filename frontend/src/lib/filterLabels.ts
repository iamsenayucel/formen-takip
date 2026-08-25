import type { FilterState } from "../hooks/useFilters";

export function periodLabel(filters: FilterState): string {
  const from = new Date(filters.dateFrom);
  const to = new Date(filters.dateTo);
  const sameMonth = from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth();
  if (sameMonth) return to.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
  const fmt = (d: Date) => d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
  return `${fmt(from)} – ${fmt(to)} ${to.getFullYear()}`;
}

export function scopeLabel(filters: FilterState): string {
  if (filters.plantIds.length === 1) return "1 Tesis";
  if (filters.plantIds.length > 1) return `${filters.plantIds.length} Tesis`;
  if (filters.factoryIds.length === 1) return "1 Fabrika";
  if (filters.factoryIds.length > 1) return `${filters.factoryIds.length} Fabrika`;
  return "Tüm Tesisler";
}

export function summarizeNames(names: string[], max = 2): string {
  if (names.length <= max) return names.join(", ");
  return `${names.slice(0, max).join(", ")} +${names.length - max}`;
}

// scopeLabel'ın soyut sayım metni ("1 Fabrika") yerine gerçek fabrika/tesis
// adlarını gösteren varyantı — isim haritaları henüz yüklenmediyse (ilk render)
// sayım metnine düşer, yanlışlıkla "Tüm Tesisler" göstermez.
export function scopeSegments(
  filters: FilterState,
  factoryNameById: Map<string, string>,
  plantNameById: Map<string, string>
): string[] {
  const segments: string[] = [];
  if (filters.factoryIds.length > 0) {
    const names = filters.factoryIds.map((id) => factoryNameById.get(id)).filter((n): n is string => !!n);
    segments.push(names.length > 0 ? summarizeNames(names) : `${filters.factoryIds.length} Fabrika`);
  }
  if (filters.plantIds.length > 0) {
    const names = filters.plantIds.map((id) => plantNameById.get(id)).filter((n): n is string => !!n);
    segments.push(names.length > 0 ? summarizeNames(names) : `${filters.plantIds.length} Tesis`);
  }
  if (segments.length === 0) segments.push("Tüm Tesisler");
  return segments;
}
