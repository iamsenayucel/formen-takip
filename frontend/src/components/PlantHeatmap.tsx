import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlants } from "../api/hooks";
import { Card, ErrorState, LoadingState } from "./StateViews";
import { GroupBadge } from "./GroupBadge";
import type { DistributionItem, PlantGroupRef, PlantListItem } from "../api/types";

const NO_DATA_COLOR = "#94a3b8";

type ViewMode = "sequence" | "group";

function HeatmapCell({
  plant,
  dimmed,
  onNavigate,
}: {
  plant: PlantListItem;
  dimmed: boolean;
  onNavigate: (id: string) => void;
}) {
  const [hover, setHover] = useState(false);
  const hasData = plant.recordCount > 0;
  const color = hasData ? plant.level.color : NO_DATA_COLOR;
  const group = plant.group;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onNavigate(plant.id)}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onFocus={() => setHover(true)}
        onBlur={() => setHover(false)}
        className="relative flex h-10 w-full items-center justify-center rounded text-[11px] font-semibold tabular-nums transition-all duration-150 hover:z-10 hover:scale-105 max-[1439px]:h-8 max-[1439px]:text-[10px]"
        style={{ background: `${color}26`, color, border: `1px solid ${color}66`, opacity: dimmed ? 0.28 : 1 }}
      >
        {String(plant.sequenceNumber).padStart(2, "0")}
        {group && (
          <span
            className="pointer-events-none absolute right-0.5 top-0.5 text-[9px] font-semibold leading-none"
            style={{ color: "var(--text-primary)" }}
          >
            {group.code}
          </span>
        )}
      </button>
      {hover && (
        <div
          className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-1.5 w-52 -translate-x-1/2 rounded-md p-2.5 text-xs shadow-lg"
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
        >
          <p className="font-semibold">{plant.name}</p>
          {group && (
            <>
              <p style={{ color: "var(--text-muted)" }}>
                Grup: <span style={{ color: "var(--text-primary)" }}>{group.code}</span>
              </p>
              <p style={{ color: "var(--text-muted)" }}>
                Şef: <span style={{ color: "var(--text-primary)" }}>{group.supervisor.name}</span>
              </p>
            </>
          )}
          {hasData ? (
            <>
              <p className="mt-1">
                Tesis Puanı: <span className="font-medium tabular-nums">{plant.totalScore.toFixed(1)}</span>
              </p>
              {group && (
                <p>
                  Grup Puanı: <span className="font-medium tabular-nums">{group.score.toFixed(1)}</span>
                </p>
              )}
              <p>
                Durum: <span className="font-medium">{plant.level.name}</span>
              </p>
              <p style={{ color: "var(--text-muted)" }}>{plant.activeForemanCount} aktif formen</p>
            </>
          ) : (
            <p className="mt-1" style={{ color: "var(--text-muted)" }}>
              Bu dönem için veri yok
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SequenceFactorySection({
  code,
  plants,
  selectedGroupId,
  onNavigate,
}: {
  code: string;
  plants: PlantListItem[];
  selectedGroupId: string | null;
  onNavigate: (id: string) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide max-[1439px]:mb-1.5" style={{ color: "var(--text-muted)" }}>
        {code}
      </p>
      <div className="grid grid-cols-6 gap-1.5 sm:grid-cols-9 md:grid-cols-12 max-[1439px]:gap-1">
        {plants.map((p) => (
          <HeatmapCell
            key={p.id}
            plant={p}
            dimmed={selectedGroupId != null && p.group?.id !== selectedGroupId}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </div>
  );
}

function GroupSection({
  group,
  plants,
  selectedGroupId,
  onNavigate,
}: {
  group: PlantGroupRef;
  plants: PlantListItem[];
  selectedGroupId: string | null;
  onNavigate: (id: string) => void;
}) {
  const dimmed = selectedGroupId != null && group.id !== selectedGroupId;
  return (
    <div className="flex flex-col gap-1.5 transition-opacity duration-150" style={{ opacity: dimmed ? 0.35 : 1 }}>
      <p className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
        <GroupBadge code={group.code} />
        {group.supervisor.name}
        <span className="tabular-nums" style={{ color: "var(--text-muted)" }}>
          · {group.score.toFixed(1)}
        </span>
        {group.foremen.length > 0 && (
          <span className="font-normal" style={{ color: "var(--text-muted)" }}>
            · Formenler: {group.foremen.map((f) => f.name).join(", ")}
          </span>
        )}
      </p>
      <div className="grid grid-cols-6 gap-1.5 sm:grid-cols-9 md:grid-cols-12 max-[1439px]:gap-1">
        {plants.map((p) => (
          <HeatmapCell key={p.id} plant={p} dimmed={false} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}

function ViewModeToggle({ mode, onChange }: { mode: ViewMode; onChange: (mode: ViewMode) => void }) {
  const options: { key: ViewMode; label: string }[] = [
    { key: "sequence", label: "Tesis Sırası" },
    { key: "group", label: "Grup Bazlı" },
  ];
  return (
    <div className="inline-flex rounded-md p-0.5" style={{ background: "var(--surface-muted)", border: "1px solid var(--border)" }}>
      {options.map((opt) => (
        <button
          key={opt.key}
          type="button"
          onClick={() => onChange(opt.key)}
          aria-pressed={mode === opt.key}
          className="rounded px-2.5 py-1 text-[12px] font-medium transition-colors max-[1439px]:px-2 max-[1439px]:py-0.5 max-[1439px]:text-[11px]"
          style={{
            background: mode === opt.key ? "var(--surface)" : "transparent",
            color: mode === opt.key ? "var(--primary)" : "var(--text-secondary)",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function PlantHeatmap({
  filters,
  levels,
  selectedGroupId,
  onSelectGroup,
}: {
  filters: Record<string, string | number | undefined>;
  levels: DistributionItem[] | undefined;
  selectedGroupId: string | null;
  onSelectGroup: (id: string | null) => void;
}) {
  const navigate = useNavigate();
  const plants = usePlants({ ...filters, sort_by: "sequence", sort_dir: "asc" }, 50);
  const [viewMode, setViewMode] = useState<ViewMode>("sequence");

  const items = useMemo(() => plants.data?.pages.flatMap((page) => page.items) ?? [], [plants.data]);

  const sequenceSections = useMemo(() => {
    const byFactory = new Map<string, PlantListItem[]>();
    for (const p of items) {
      const key = p.factory?.code ?? "?";
      if (!byFactory.has(key)) byFactory.set(key, []);
      byFactory.get(key)!.push(p);
    }
    return [...byFactory.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [items]);

  const groupSections = useMemo(() => {
    const byFactory = new Map<string, PlantListItem[]>();
    for (const p of items) {
      const key = p.factory?.code ?? "?";
      if (!byFactory.has(key)) byFactory.set(key, []);
      byFactory.get(key)!.push(p);
    }
    const factories = [...byFactory.entries()].sort(([a], [b]) => a.localeCompare(b));
    return factories.map(([factoryCode, factoryPlants]) => {
      const byGroup = new Map<string, { group: PlantGroupRef; plants: PlantListItem[] }>();
      for (const p of factoryPlants) {
        if (!p.group) continue;
        if (!byGroup.has(p.group.id)) byGroup.set(p.group.id, { group: p.group, plants: [] });
        byGroup.get(p.group.id)!.plants.push(p);
      }
      const groups = [...byGroup.values()].sort((a, b) => a.group.code.localeCompare(b.group.code, "tr", { numeric: true }));
      return { factoryCode, groups };
    });
  }, [items]);

  const groupOptions = useMemo(() => {
    const byId = new Map<string, PlantGroupRef>();
    for (const p of items) {
      if (p.group && !byId.has(p.group.id)) byId.set(p.group.id, p.group);
    }
    return [...byId.values()].sort((a, b) => a.code.localeCompare(b.code, "tr", { numeric: true }));
  }, [items]);

  const onNavigate = (id: string) => navigate(`/plants/${id}`);

  return (
    <Card
      title="Tesis Performans Haritası"
      action={
        <div className="flex flex-wrap items-center justify-end gap-2">
          <ViewModeToggle mode={viewMode} onChange={setViewMode} />
          <select
            value={selectedGroupId ?? ""}
            onChange={(e) => onSelectGroup(e.target.value || null)}
            aria-label="Gruba göre vurgula"
            className="rounded-md border px-2.5 py-1.5 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 max-[1439px]:px-2 max-[1439px]:py-1 max-[1439px]:text-xs"
            style={{ borderColor: "var(--border-strong)", background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">Tümü</option>
            {groupOptions.map((g) => (
              <option key={g.id} value={g.id}>
                {g.code} · {g.supervisor.name}
              </option>
            ))}
          </select>
        </div>
      }
    >
      {plants.isLoading && <LoadingState />}
      {plants.isError && <ErrorState />}
      {plants.data && (
        <div className="flex flex-col gap-5 max-[1439px]:gap-3">
          {viewMode === "sequence"
            ? sequenceSections.map(([code, factoryPlants]) => (
                <SequenceFactorySection
                  key={code}
                  code={code}
                  plants={factoryPlants}
                  selectedGroupId={selectedGroupId}
                  onNavigate={onNavigate}
                />
              ))
            : groupSections.map(({ factoryCode, groups }) => (
                <div key={factoryCode} className="flex flex-col gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                    {factoryCode}
                  </p>
                  {groups.map(({ group, plants: groupPlants }) => (
                    <GroupSection
                      key={group.id}
                      group={group}
                      plants={groupPlants}
                      selectedGroupId={selectedGroupId}
                      onNavigate={onNavigate}
                    />
                  ))}
                </div>
              ))}

          <div
            className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-3 text-xs"
            style={{ borderTop: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            {(levels ?? []).map((lv) => (
              <span key={lv.name} className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: lv.color }} />
                {lv.name}
              </span>
            ))}
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: NO_DATA_COLOR }} />
              Veri Yok
            </span>
            <span className="flex items-center gap-1.5 border-l pl-4" style={{ borderColor: "var(--border-subtle)" }}>
              <GroupBadge code="G03" />
              Grup
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
