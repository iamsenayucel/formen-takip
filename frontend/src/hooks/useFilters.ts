import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface FilterState {
  dateFrom: string;
  dateTo: string;
  plantIds: string[];
  factoryIds: string[];
  chiefIds: string[];
  shiftIds: string[];
  kpiIds: string[];
  foremanIds: string[];
}

// Business tarihler backend ile aynı sözleşmeyi kullanır: Europe/Istanbul takvim
// günü. Tarayıcının kendi işletim sistemi saat dilimi farklı olabileceğinden
// (veya Date#toISOString() gibi UTC'ye çeviren API'ler) "bugün" burada her
// zaman Europe/Istanbul'a göre hesaplanır — browser timezone'u business
// timezone sanılmaz.
const ISTANBUL_DATE_FORMATTER = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul" });

function todayIso(): string {
  return ISTANBUL_DATE_FORMATTER.format(new Date());
}

function daysAgoIso(days: number): string {
  const [year, month, day] = todayIso().split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day - days));
  return shifted.toISOString().slice(0, 10);
}

function istanbulCurrentYear(): number {
  return Number(todayIso().slice(0, 4));
}

export function defaultDateRange(): [string, string] {
  return [daysAgoIso(30), todayIso()];
}

export function businessTodayIso(): string {
  return todayIso();
}

const DEFAULTS: FilterState = {
  dateFrom: daysAgoIso(30),
  dateTo: todayIso(),
  plantIds: [],
  factoryIds: [],
  chiefIds: [],
  shiftIds: [],
  kpiIds: [],
  foremanIds: [],
};

function parseList(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<FilterState>(
    () => ({
      dateFrom: searchParams.get("date_from") || DEFAULTS.dateFrom,
      dateTo: searchParams.get("date_to") || DEFAULTS.dateTo,
      plantIds: parseList(searchParams.get("plant_ids")),
      factoryIds: parseList(searchParams.get("factory_ids")),
      chiefIds: parseList(searchParams.get("chief_ids")),
      shiftIds: parseList(searchParams.get("shift_ids")),
      kpiIds: parseList(searchParams.get("kpi_ids")),
      foremanIds: parseList(searchParams.get("foreman_ids")),
    }),
    [searchParams]
  );

  const setFilters = useCallback(
    (partial: Partial<FilterState>) => {
      const next = { ...filters, ...partial };
      const params = new URLSearchParams(searchParams);
      const setOrDelete = (key: string, value: string) => {
        if (value) params.set(key, value);
        else params.delete(key);
      };
      params.set("date_from", next.dateFrom);
      params.set("date_to", next.dateTo);
      setOrDelete("plant_ids", next.plantIds.join(","));
      setOrDelete("factory_ids", next.factoryIds.join(","));
      setOrDelete("chief_ids", next.chiefIds.join(","));
      setOrDelete("shift_ids", next.shiftIds.join(","));
      setOrDelete("kpi_ids", next.kpiIds.join(","));
      setOrDelete("foreman_ids", next.foremanIds.join(","));
      setSearchParams(params, { replace: true });
    },
    [filters, searchParams, setSearchParams]
  );

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const asQueryParams = useMemo(
    () => ({
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      plant_ids: filters.plantIds.join(",") || undefined,
      factory_ids: filters.factoryIds.join(",") || undefined,
      chief_ids: filters.chiefIds.join(",") || undefined,
      shift_ids: filters.shiftIds.join(",") || undefined,
      kpi_ids: filters.kpiIds.join(",") || undefined,
      foreman_ids: filters.foremanIds.join(",") || undefined,
    }),
    [filters]
  );

  return { filters, setFilters, clearFilters, asQueryParams };
}

export const DATE_PRESETS: { label: string; getRange: () => [string, string] }[] = [
  { label: "Bugün", getRange: () => [todayIso(), todayIso()] },
  { label: "Dün", getRange: () => [daysAgoIso(1), daysAgoIso(1)] },
  { label: "Son 7 Gün", getRange: () => [daysAgoIso(7), todayIso()] },
  { label: "Son 30 Gün", getRange: () => [daysAgoIso(30), todayIso()] },
  { label: "Son 3 Ay", getRange: () => [daysAgoIso(90), todayIso()] },
  { label: "Son 6 Ay", getRange: () => [daysAgoIso(180), todayIso()] },
  { label: "Bu Yıl", getRange: () => [`${istanbulCurrentYear()}-01-01`, todayIso()] },
  { label: "Son 12 Ay", getRange: () => [daysAgoIso(365), todayIso()] },
];
