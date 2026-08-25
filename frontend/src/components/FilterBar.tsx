import { useMemo, useState } from "react";
import { ChevronDown, SlidersHorizontal, X } from "lucide-react";
import { useFilterOptions, useForemen, useForemenByIds } from "../api/hooks";
import { businessTodayIso, DATE_PRESETS, defaultDateRange, type FilterState } from "../hooks/useFilters";
import { useDismissablePopover } from "../hooks/useDismissablePopover";
import { summarizeNames } from "../lib/filterLabels";

interface Props {
  filters: FilterState;
  setFilters: (partial: Partial<FilterState>) => void;
  clearFilters: () => void;
}

const inputClass =
  "rounded-md border px-2.5 py-1.5 text-[13px] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 max-[1439px]:px-2 max-[1439px]:py-1 max-[1439px]:text-xs";
const inputStyle = { borderColor: "var(--border-strong)", background: "var(--surface)", color: "var(--text-primary)" };

export interface MultiSelectOption {
  id: string;
  name: string;
  hint?: string;
}

const SEARCH_THRESHOLD = 10;

export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  disabled,
}: {
  label: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  const close = () => {
    setOpen(false);
    setQuery("");
  };
  const triggerRef = useDismissablePopover(open, close);

  const showSearch = options.length > SEARCH_THRESHOLD;
  const visibleOptions = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("tr");
    if (!q) return options;
    return options.filter(
      (o) =>
        o.name.toLocaleLowerCase("tr").includes(q) || (o.hint ?? "").toLocaleLowerCase("tr").includes(q)
    );
  }, [options, query]);

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => (open ? close() : setOpen(true))}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex min-w-32 items-center justify-between gap-2 ${inputClass} disabled:opacity-40`}
        style={inputStyle}
      >
        <span>
          {label}
          {selected.length > 0 && <span className="ml-1 font-medium" style={{ color: "var(--primary)" }}>({selected.length})</span>}
        </span>
        <ChevronDown size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div
            className="absolute z-20 mt-1 w-72 rounded-md shadow-lg"
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
          >
            {showSearch && (
              <div className="p-1.5" style={{ borderBottom: "1px solid var(--border)" }}>
                <input
                  autoFocus
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ara..."
                  aria-label={`${label} ara`}
                  className="w-full rounded border px-2 py-1 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
                  style={inputStyle}
                />
              </div>
            )}
            <div className="max-h-64 overflow-auto p-1">
              {visibleOptions.length === 0 && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {options.length === 0 ? "Seçenek yok" : "Eşleşen sonuç yok"}
                </div>
              )}
              {visibleOptions.map((opt) => (
                <label
                  key={opt.id}
                  className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-[var(--page-bg)]"
                  style={{ color: "var(--text-primary)" }}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 shrink-0"
                    checked={selected.includes(opt.id)}
                    onChange={() => toggle(opt.id)}
                  />
                  <span className="min-w-0">
                    <span className="block truncate">{opt.name}</span>
                    {opt.hint && (
                      <span className="block truncate text-xs" style={{ color: "var(--text-muted)" }}>
                        {opt.hint}
                      </span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ForemanFilterSelect({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const results = useForemen({ search: query || undefined }, 8);
  const resultItems = results.data?.pages.flatMap((page) => page.items) ?? [];

  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  const close = () => {
    setOpen(false);
    setQuery("");
  };
  const triggerRef = useDismissablePopover(open, close);

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => (open ? close() : setOpen(true))}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex min-w-32 items-center justify-between gap-2 ${inputClass}`}
        style={inputStyle}
      >
        <span>
          Formen
          {selected.length > 0 && <span className="ml-1 font-medium" style={{ color: "var(--primary)" }}>({selected.length})</span>}
        </span>
        <ChevronDown size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div
            className="absolute z-20 mt-1 w-72 rounded-md shadow-lg"
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
          >
            <div className="p-1.5" style={{ borderBottom: "1px solid var(--border)" }}>
              <input
                autoFocus
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ad, soyad veya sicil no ara..."
                aria-label="Formen ara"
                className="w-full rounded border px-2 py-1 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
                style={inputStyle}
              />
            </div>
            <div className="max-h-64 overflow-auto p-1">
              {results.isLoading && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>Aranıyor...</div>
              )}
              {results.data && resultItems.length === 0 && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>Eşleşen formen yok</div>
              )}
              {resultItems.map((f) => (
                <label
                  key={f.id}
                  className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-[var(--page-bg)]"
                  style={{ color: "var(--text-primary)" }}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 shrink-0"
                    checked={selected.includes(f.id)}
                    onChange={() => toggle(f.id)}
                  />
                  <span className="min-w-0 truncate">
                    {f.fullName} <span style={{ color: "var(--text-muted)" }}>— {f.employeeNumber}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface ActiveChip {
  key: string;
  label: string;
  onRemove: () => void;
}

function ActiveFiltersStrip({ chips }: { chips: ActiveChip[] }) {
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t px-3 py-2" style={{ borderColor: "var(--border)" }}>
      <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
        Aktif filtreler:
      </span>
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
          style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
        >
          {chip.label}
          <button type="button" onClick={chip.onRemove} className="hover:opacity-70" aria-label={`${chip.label} filtresini kaldır`}>
            <X size={11} strokeWidth={2.5} />
          </button>
        </span>
      ))}
    </div>
  );
}

export function FilterBar({ filters, setFilters, clearFilters }: Props) {
  const { data: options, isLoading } = useFilterOptions(
    filters.plantIds.join(",") || undefined,
    filters.factoryIds.join(",") || undefined
  );

  const advancedActiveCount = filters.chiefIds.length + filters.shiftIds.length + filters.kpiIds.length + filters.foremanIds.length;
  const [advancedOpen, setAdvancedOpen] = useState(advancedActiveCount > 0);

  const activeCount =
    filters.plantIds.length + filters.factoryIds.length + filters.chiefIds.length +
    filters.shiftIds.length + filters.kpiIds.length + filters.foremanIds.length;

  const foremenLookup = useForemenByIds(filters.foremanIds);
  const foremanNameById = useMemo(
    () => new Map((foremenLookup.data?.items ?? []).map((f) => [f.id, f.fullName])),
    [foremenLookup.data]
  );

  const plantNameById = useMemo(
    () => new Map((options?.plants ?? []).map((p) => [p.id, p.name])),
    [options]
  );
  const chiefOptions = useMemo(
    () =>
      (options?.chiefs ?? []).map((c) => {
        const names = c.plantIds.map((id) => plantNameById.get(id)).filter((n): n is string => !!n);
        return {
          id: c.id,
          name: c.name,
          hint: names.length > 2 ? `${names.slice(0, 2).join(", ")} +${names.length - 2}` : names.join(", "),
        };
      }),
    [options, plantNameById]
  );

  const plantIdsByChief = useMemo(
    () => new Map((options?.chiefs ?? []).map((c) => [c.id, c.plantIds])),
    [options]
  );
  const factoryIdByPlant = useMemo(
    () => new Map((options?.plants ?? []).map((p) => [p.id, p.factoryId])),
    [options]
  );

  const handleFactoryChange = (ids: string[]) => {
    const allowed = new Set(ids);
    const plantStillValid = (plantId: string) =>
      allowed.size === 0 || allowed.has(factoryIdByPlant.get(plantId) ?? "");
    setFilters({
      factoryIds: ids,
      plantIds: filters.plantIds.filter(plantStillValid),
      chiefIds: filters.chiefIds.filter((chiefId) => (plantIdsByChief.get(chiefId) ?? []).some(plantStillValid)),
    });
  };

  const handlePlantChange = (ids: string[]) => {
    const allowed = new Set(ids);
    setFilters({
      plantIds: ids,
      chiefIds:
        allowed.size === 0
          ? filters.chiefIds
          : filters.chiefIds.filter((chiefId) => (plantIdsByChief.get(chiefId) ?? []).some((id) => allowed.has(id))),
    });
  };

  const factoryNameById = useMemo(
    () => new Map((options?.factories ?? []).map((f) => [f.id, f.name])),
    [options]
  );
  const chiefNameById = useMemo(() => new Map(chiefOptions.map((c) => [c.id, c.name])), [chiefOptions]);
  const shiftNameById = useMemo(
    () => new Map((options?.shifts ?? []).map((s) => [s.id, s.name])),
    [options]
  );
  const kpiNameById = useMemo(
    () => new Map((options?.kpis ?? []).map((k) => [k.id, k.name])),
    [options]
  );

  const dateRangeLabel = `${filters.dateFrom} – ${filters.dateTo}`;

  const chips: ActiveChip[] = [
    { key: "date", label: `Tarih: ${dateRangeLabel}`, onRemove: () => { const [from, to] = defaultDateRange(); setFilters({ dateFrom: from, dateTo: to }); } },
    ...(filters.factoryIds.length > 0
      ? [{
          key: "factory",
          label: `Fabrika: ${summarizeNames(filters.factoryIds.map((id) => factoryNameById.get(id) ?? id))}`,
          onRemove: () => handleFactoryChange([]),
        }]
      : []),
    ...(filters.plantIds.length > 0
      ? [{
          key: "plant",
          label: `Tesis: ${summarizeNames(filters.plantIds.map((id) => plantNameById.get(id) ?? id))}`,
          onRemove: () => handlePlantChange([]),
        }]
      : []),
    ...(filters.chiefIds.length > 0
      ? [{
          key: "chief",
          label: `Şef: ${summarizeNames(filters.chiefIds.map((id) => chiefNameById.get(id) ?? id))}`,
          onRemove: () => setFilters({ chiefIds: [] }),
        }]
      : []),
    ...(filters.shiftIds.length > 0
      ? [{
          key: "shift",
          label: `Vardiya: ${summarizeNames(filters.shiftIds.map((id) => shiftNameById.get(id) ?? id))}`,
          onRemove: () => setFilters({ shiftIds: [] }),
        }]
      : []),
    ...(filters.kpiIds.length > 0
      ? [{
          key: "kpi",
          label: `KPI: ${summarizeNames(filters.kpiIds.map((id) => kpiNameById.get(id) ?? id))}`,
          onRemove: () => setFilters({ kpiIds: [] }),
        }]
      : []),
    ...(filters.foremanIds.length > 0
      ? [{
          key: "foreman",
          label: `Formen: ${summarizeNames(filters.foremanIds.map((id) => foremanNameById.get(id) ?? id))}`,
          onRemove: () => setFilters({ foremanIds: [] }),
        }]
      : []),
  ];

  return (
    <div className="sticky top-0 z-30 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)", boxShadow: "var(--shadow-panel)" }}>
      <div className="flex flex-wrap items-center gap-2 p-3 max-[1439px]:gap-1.5 max-[1439px]:p-2">
        <select
          className={inputClass}
          style={inputStyle}
          onChange={(e) => {
            const preset = DATE_PRESETS.find((p) => p.label === e.target.value);
            if (preset) {
              const [from, to] = preset.getRange();
              setFilters({ dateFrom: from, dateTo: to });
            }
          }}
          defaultValue=""
        >
          <option value="" disabled>
            Hazır tarih aralığı
          </option>
          {DATE_PRESETS.map((p) => (
            <option key={p.label} value={p.label}>
              {p.label}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={filters.dateFrom}
          max={filters.dateTo}
          onChange={(e) => setFilters({ dateFrom: e.target.value })}
          className={inputClass}
          style={inputStyle}
        />
        <span style={{ color: "var(--text-muted)" }}>–</span>
        <input
          type="date"
          value={filters.dateTo}
          min={filters.dateFrom}
          max={businessTodayIso()}
          onChange={(e) => setFilters({ dateTo: e.target.value })}
          className={inputClass}
          style={inputStyle}
        />

        <div className="mx-1 h-6 w-px" style={{ background: "var(--border)" }} />

        <button
          type="button"
          disabled
          title="Sistem şu an yalnızca Karaman lokasyonunu kapsıyor"
          className={`flex min-w-28 items-center justify-between gap-2 ${inputClass} disabled:opacity-70`}
          style={inputStyle}
        >
          <span>Lokasyon: Karaman</span>
        </button>

        <MultiSelect
          label="Fabrika"
          options={options?.factories ?? []}
          selected={filters.factoryIds}
          onChange={handleFactoryChange}
          disabled={isLoading}
        />
        <MultiSelect
          label="Tesis"
          options={options?.plants ?? []}
          selected={filters.plantIds}
          onChange={handlePlantChange}
          disabled={isLoading}
        />

        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          aria-expanded={advancedOpen}
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-colors hover:bg-[var(--page-bg)]"
          style={{ color: advancedOpen || advancedActiveCount > 0 ? "var(--primary)" : "var(--text-secondary)" }}
        >
          <SlidersHorizontal size={13} strokeWidth={2} />
          Gelişmiş filtreler
          {advancedActiveCount > 0 && (
            <span className="font-semibold">({advancedActiveCount})</span>
          )}
          <ChevronDown
            size={13}
            strokeWidth={2}
            className={`transition-transform duration-150 ${advancedOpen ? "rotate-180" : ""}`}
          />
        </button>

        {activeCount > 0 && (
          <button
            onClick={clearFilters}
            className="ml-auto flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
            style={{ color: "var(--primary)" }}
          >
            <X size={13} strokeWidth={2} />
            Filtreleri temizle ({activeCount})
          </button>
        )}
      </div>

      {advancedOpen && (
        <div
          className="flex flex-wrap items-center gap-2 px-3 pb-3"
          style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.75rem" }}
        >
          <span className="text-label mr-1" style={{ color: "var(--text-muted)" }}>
            Detay:
          </span>
          <MultiSelect
            label="Şef"
            options={chiefOptions}
            selected={filters.chiefIds}
            onChange={(ids) => setFilters({ chiefIds: ids })}
            disabled={isLoading}
          />
          <MultiSelect
            label="Vardiya"
            options={options?.shifts ?? []}
            selected={filters.shiftIds}
            onChange={(ids) => setFilters({ shiftIds: ids })}
            disabled={isLoading}
          />
          <MultiSelect
            label="KPI"
            options={options?.kpis ?? []}
            selected={filters.kpiIds}
            onChange={(ids) => setFilters({ kpiIds: ids })}
            disabled={isLoading}
          />
          <ForemanFilterSelect
            selected={filters.foremanIds}
            onChange={(ids) => setFilters({ foremanIds: ids })}
          />
        </div>
      )}

      <ActiveFiltersStrip chips={chips} />
    </div>
  );
}
