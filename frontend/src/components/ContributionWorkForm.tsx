import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Plus, Trash2, TriangleAlert, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useCreateContributionWork, useFilterOptions, useUpdateContributionWork } from "../api/hooks";
import type {
  ContributionCurrency, ContributionGainInput, ContributionTimeUnit, ContributionWorkCreatePayload,
  ContributionWorkItem, ContributionWorkType, FinancialGainStatus, GainPeriod, ImpactLevel,
  OtherGainType, RepeatPeriod,
} from "../api/types";
import { computeChange, computeMonthlyTotal, computeTimeSaving, durationToMinutes, formatMinutes } from "../lib/contributionCalc";
import { CREATABLE_WORK_TYPES, IMPACT_LEVEL_LABELS, WORK_TYPE_LABELS } from "../lib/contributionTheme";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { ForemanMultiSelect, type SelectedForeman } from "./ForemanMultiSelect";
import { MultiSelect } from "./FilterBar";
import { useModalA11y } from "../hooks/useModalA11y";

const WORK_TYPE_OPTIONS = CREATABLE_WORK_TYPES.map((t) => [t, WORK_TYPE_LABELS[t]] as [ContributionWorkType, string]);
const IMPACT_OPTIONS = Object.entries(IMPACT_LEVEL_LABELS) as [ImpactLevel, string][];

const FINANCIAL_STATUS_LABELS: Record<FinancialGainStatus, string> = {
  yes: "Evet", no: "Hayır", not_calculated: "Henüz hesaplanmadı",
};
const GAIN_PERIOD_LABELS: Record<GainPeriod, string> = { one_time: "Tek seferlik", monthly: "Aylık", yearly: "Yıllık" };
const TIME_UNIT_LABELS: Record<ContributionTimeUnit, string> = { second: "Saniye", minute: "Dakika", hour: "Saat" };
const REPEAT_PERIOD_LABELS: Record<RepeatPeriod, string> = { daily: "Günlük", weekly: "Haftalık", monthly: "Aylık" };
const GAIN_TYPE_LABELS: Record<OtherGainType, string> = {
  capacity_increase: "Üretim kapasitesi artışı", downtime_reduction: "Duruş süresi azalması",
  gsf_reduction: "GSF azalması", scrap_reduction: "Iskarta azalması", slow_running_reduction: "Ağır gitme azalması",
  safety_risk_reduction: "İş kazası riskinin azalması", energy_reduction: "Enerji tüketimi azalması",
  labor_saving: "İş gücü tasarrufu", quality_defect_reduction: "Kalite hatası azalması", other: "Diğer",
};

function Section({ title, subtitle, children, defaultOpen = true, hasError }: {
  title: string; subtitle?: string; children: ReactNode; defaultOpen?: boolean; hasError?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg" style={{ border: `1px solid ${hasError ? "var(--status-negative)" : "var(--border)"}` }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3"
      >
        <div className="text-left">
          <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
            {hasError && <TriangleAlert size={13} strokeWidth={2.5} color="var(--status-negative)" />}
          </div>
          {subtitle && <div className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{subtitle}</div>}
        </div>
        <ChevronDown size={16} strokeWidth={2} className={open ? "rotate-180 transition-transform" : "transition-transform"} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && <div className="flex flex-col gap-3 border-t px-4 py-4" style={{ borderColor: "var(--border)" }}>{children}</div>}
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-xs font-medium" style={{ color: "var(--status-negative)" }}>{message}</p>;
}

interface Props {
  existing?: ContributionWorkItem;
  onClose: () => void;
}

export function ContributionWorkForm({ existing, onClose }: Props) {
  const isEdit = !!existing;
  const navigate = useNavigate();
  const { user } = useAuth();
  const filterOptions = useFilterOptions();
  const createMutation = useCreateContributionWork();
  const updateMutation = useUpdateContributionWork();

  const [title, setTitle] = useState(existing?.title ?? "");
  const [workType, setWorkType] = useState<ContributionWorkType | "">(existing?.workType ?? "");
  const [workTypeOtherNote, setWorkTypeOtherNote] = useState(existing?.workTypeOtherNote ?? "");
  const [foremen, setForemen] = useState<SelectedForeman[]>(existing?.foremen.map((f) => ({ id: f.id, name: f.name })) ?? []);
  const [factoryIds, setFactoryIds] = useState<string[]>(
    Array.from(new Set((existing?.plants ?? []).map((p) => p.factoryId)))
  );
  const [plantIds, setPlantIds] = useState<string[]>((existing?.plants ?? []).map((p) => p.id));
  const [dateMode, setDateMode] = useState<"single" | "range">(existing?.workDateEnd ? "range" : "single");
  const [workDate, setWorkDate] = useState(existing?.workDate ?? "");
  const [workDateEnd, setWorkDateEnd] = useState(existing?.workDateEnd ?? "");
  const [impactLevel, setImpactLevel] = useState<ImpactLevel | "">(existing?.impactLevel ?? "medium");

  const [summary, setSummary] = useState(existing?.summary ?? "");
  const [detailedDescription, setDetailedDescription] = useState(existing?.detailedDescription ?? "");
  const [problemDescription, setProblemDescription] = useState(existing?.problemDescription ?? "");
  const [solutionDescription, setSolutionDescription] = useState(existing?.solutionDescription ?? "");
  const [resultDescription, setResultDescription] = useState(existing?.resultDescription ?? "");

  const [financialGainStatus, setFinancialGainStatus] = useState<FinancialGainStatus>(existing?.financialGainStatus ?? "not_calculated");
  const [gainAmount, setGainAmount] = useState(existing?.gainAmount?.toString() ?? "");
  const [currency, setCurrency] = useState<ContributionCurrency>(existing?.currency ?? "TRY");
  const [gainPeriod, setGainPeriod] = useState<GainPeriod | "">(existing?.gainPeriod ?? "");

  const [previousDuration, setPreviousDuration] = useState(existing?.previousDuration?.toString() ?? "");
  const [newDuration, setNewDuration] = useState(existing?.newDuration?.toString() ?? "");
  const [durationUnit, setDurationUnit] = useState<ContributionTimeUnit>(existing?.durationUnit ?? "minute");
  const [repeatPeriod, setRepeatPeriod] = useState<RepeatPeriod | "">(existing?.repeatPeriod ?? "");

  const [gains, setGains] = useState<ContributionGainInput[]>(
    existing?.gains.map((g) => ({
      gainType: g.gainType, gainTypeOtherNote: g.gainTypeOtherNote ?? undefined,
      previousValue: g.previousValue ?? undefined, nextValue: g.nextValue ?? undefined,
      unit: g.unit ?? undefined, measurementPeriod: g.measurementPeriod ?? undefined, description: g.description ?? undefined,
    })) ?? []
  );

  const [isStandardized, setIsStandardized] = useState(existing?.isStandardized ?? false);
  const [isApplicableOtherPlants, setIsApplicableOtherPlants] = useState(existing?.isApplicableOtherPlants ?? false);
  const [isPermanentSolution, setIsPermanentSolution] = useState(existing?.isPermanentSolution ?? false);
  const [workInstructionUpdated, setWorkInstructionUpdated] = useState(existing?.workInstructionUpdated ?? false);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const markDirty = <T,>(setter: (v: T) => void) => (v: T) => {
    setDirty(true);
    setter(v);
  };

  const plantsForFactory = useMemo(
    () => (filterOptions.data?.plants ?? []).filter((p) => factoryIds.length === 0 || factoryIds.includes(p.factoryId)),
    [filterOptions.data, factoryIds]
  );

  // Türü WORK_TYPE_OPTIONS içinden kaldırılmış bir çalışma düzenleniyorsa kullanıcı bilerek
  // değiştirene kadar alanın boş render edilmemesi için mevcut tür seçilebilir kalır.
  const workTypeOptions = useMemo(() => {
    if (existing?.workType && !WORK_TYPE_OPTIONS.some(([v]) => v === existing.workType)) {
      return [...WORK_TYPE_OPTIONS, [existing.workType, `${WORK_TYPE_LABELS[existing.workType]} (kaldırıldı)`] as [ContributionWorkType, string]];
    }
    return WORK_TYPE_OPTIONS;
  }, [existing?.workType]);

  const prevDurationNum = previousDuration === "" ? null : Number(previousDuration);
  const newDurationNum = newDuration === "" ? null : Number(newDuration);
  const perOccurrenceSaving = computeTimeSaving(prevDurationNum, newDurationNum);
  const newDurationInvalid = prevDurationNum != null && newDurationNum != null && newDurationNum >= prevDurationNum;
  const perOccurrenceMinutes = durationToMinutes(perOccurrenceSaving, durationUnit);
  const monthlyTotal = computeMonthlyTotal(perOccurrenceMinutes, repeatPeriod || null, repeatPeriod ? 1 : null);

  const handleClose = () => {
    if (dirty && !window.confirm("Kaydedilmemiş değişiklikleriniz var. Çıkmak istediğinize emin misiniz?")) return;
    onClose();
  };

  const containerRef = useModalA11y(handleClose);

  function addGain() {
    setDirty(true);
    setGains((g) => [...g, { gainType: "other" }]);
  }
  function updateGain(index: number, patch: Partial<ContributionGainInput>) {
    setDirty(true);
    setGains((g) => g.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }
  function removeGain(index: number) {
    setDirty(true);
    setGains((g) => g.filter((_, i) => i !== index));
  }

  function buildPayload(status: "draft" | "published"): ContributionWorkCreatePayload {
    return {
      title, status,
      workType: workType || undefined,
      workTypeOtherNote: workTypeOtherNote || undefined,
      summary: summary || undefined,
      detailedDescription: detailedDescription || undefined,
      problemDescription: problemDescription || undefined,
      solutionDescription: solutionDescription || undefined,
      resultDescription: resultDescription || undefined,
      foremanIds: foremen.map((f) => f.id),
      plantIds,
      workDate: workDate || undefined,
      workDateEnd: dateMode === "range" ? workDateEnd || undefined : undefined,
      impactLevel: impactLevel || undefined,
      isStandardized,
      isApplicableOtherPlants,
      isPermanentSolution,
      workInstructionUpdated,
      financialGainStatus,
      gainAmount: gainAmount === "" ? undefined : Number(gainAmount),
      currency: financialGainStatus === "yes" ? currency : undefined,
      gainPeriod: gainPeriod || undefined,
      previousDuration: prevDurationNum ?? undefined,
      newDuration: newDurationNum ?? undefined,
      durationUnit: previousDuration || newDuration ? durationUnit : undefined,
      repeatPeriod: repeatPeriod || undefined,
      gains,
    };
  }

  async function handleSubmit(status: "draft" | "published") {
    setError(null);
    setFieldErrors({});

    if (dateMode === "range" && workDate && workDateEnd && workDateEnd < workDate) {
      setError("Bitiş tarihi başlangıç tarihinden önce olamaz.");
      return;
    }

    const payload = buildPayload(status);
    try {
      let saved: ContributionWorkItem;
      if (isEdit) {
        saved = await updateMutation.mutateAsync({ id: existing.id, payload });
      } else {
        saved = await createMutation.mutateAsync(payload);
      }
      setDirty(false);
      onClose();
      if (status === "published") {
        navigate(`/improvement-works/${saved.id}`, { state: { justPublished: true } });
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: { message?: string; errors?: Record<string, string> } } } };
      const detail = axiosErr.response?.data?.detail;
      if (axiosErr.response?.status === 422 && detail?.errors) {
        setFieldErrors(detail.errors);
        setError(detail.message ?? "Yayımlamak için zorunlu alanlar eksik.");
      } else {
        setError("Kaydedilemedi. Lütfen tekrar deneyin.");
      }
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;
  const basicsHasError = !!(fieldErrors.title || fieldErrors.workType || fieldErrors.workTypeOtherNote || fieldErrors.summary);
  const peopleHasError = !!(fieldErrors.foremanIds || fieldErrors.plantIds || fieldErrors.workDate || fieldErrors.workDateEnd);
  const flowHasError = !!(fieldErrors.problemDescription || fieldErrors.solutionDescription);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={handleClose}>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="contribution-work-form-title"
        tabIndex={-1}
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg shadow-xl focus:outline-none"
        style={{ background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-5 py-4" style={{ borderColor: "var(--border)" }}>
          <h3 id="contribution-work-form-title" className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {isEdit ? "Çalışmayı Düzenle" : "Yeni Operational Impact+ Çalışması"}
          </h3>
          <button type="button" onClick={handleClose} aria-label="Kapat" style={{ color: "var(--text-muted)" }}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        <div className="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <Section title="1. Kişiler ve Konum" subtitle="İlgili formenler, fabrika/tesis ve çalışma tarihi" hasError={peopleHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>İlgili Formen(ler)</label>
              <ForemanMultiSelect selected={foremen} onChange={markDirty(setForemen)} />
              <FieldError message={fieldErrors.foremanIds} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Fabrika(lar)</label>
                <MultiSelect
                  label="Fabrika"
                  options={(filterOptions.data?.factories ?? []).map((f) => ({ id: f.id, name: f.name, hint: f.code }))}
                  selected={factoryIds}
                  onChange={(ids) => {
                    markDirty(setFactoryIds)(ids);
                    if (ids.length > 0) {
                      setPlantIds((current) =>
                        current.filter((pid) => {
                          const plant = filterOptions.data?.plants.find((p) => p.id === pid);
                          return plant && ids.includes(plant.factoryId);
                        })
                      );
                    }
                  }}
                />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Tesis(ler)</label>
                <MultiSelect
                  label="Tesis"
                  options={plantsForFactory.map((p) => ({ id: p.id, name: p.name }))}
                  selected={plantIds}
                  onChange={markDirty(setPlantIds)}
                />
                <FieldError message={fieldErrors.plantIds} />
              </div>
            </div>

            <div>
              <label className={labelClass} style={labelStyle}>Kaydı Oluşturan Yönetici</label>
              <input disabled value={user?.fullName ?? ""} className={`${fieldClass} disabled:opacity-70`} style={fieldStyle} />
            </div>

            <div>
              <label className={labelClass} style={labelStyle}>Çalışma Tarihi</label>
              <div className="mb-2 flex gap-3 text-xs" style={{ color: "var(--text-secondary)" }}>
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={dateMode === "single"} onChange={() => markDirty(setDateMode)("single")} />
                  Tek tarih
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={dateMode === "range"} onChange={() => markDirty(setDateMode)("range")} />
                  Tarih aralığı
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input type="date" value={workDate} onChange={(e) => markDirty(setWorkDate)(e.target.value)} className={fieldClass} style={fieldStyle} />
                {dateMode === "range" && (
                  <input type="date" value={workDateEnd} min={workDate || undefined} onChange={(e) => markDirty(setWorkDateEnd)(e.target.value)} className={fieldClass} style={fieldStyle} />
                )}
              </div>
              <FieldError message={fieldErrors.workDate || fieldErrors.workDateEnd} />
            </div>
          </Section>

          <Section title="2. Temel Bilgiler" subtitle="Başlık, tür ve açıklamalar" hasError={basicsHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>Çalışma Başlığı</label>
              <input value={title} onChange={(e) => markDirty(setTitle)(e.target.value)} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.title} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Çalışma Türü</label>
                <select value={workType} onChange={(e) => markDirty(setWorkType)(e.target.value as ContributionWorkType)} className={fieldClass} style={fieldStyle}>
                  <option value="">Seçiniz</option>
                  {workTypeOptions.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <FieldError message={fieldErrors.workType} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Etki Seviyesi</label>
                <select value={impactLevel} onChange={(e) => markDirty(setImpactLevel)(e.target.value as ImpactLevel)} className={fieldClass} style={fieldStyle}>
                  {IMPACT_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>
            {workType === "other" && (
              <div>
                <label className={labelClass} style={labelStyle}>Çalışma Türünü Açıklayın</label>
                <input value={workTypeOtherNote} onChange={(e) => markDirty(setWorkTypeOtherNote)(e.target.value)} className={fieldClass} style={fieldStyle} />
                <FieldError message={fieldErrors.workTypeOtherNote} />
              </div>
            )}

            <div>
              <label className={labelClass} style={labelStyle}>Kısa Özet</label>
              <textarea value={summary} onChange={(e) => markDirty(setSummary)(e.target.value)} rows={2} maxLength={500} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.summary} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Detaylı Açıklama</label>
              <textarea value={detailedDescription} onChange={(e) => markDirty(setDetailedDescription)(e.target.value)} rows={3} className={fieldClass} style={fieldStyle} />
            </div>
          </Section>

          <Section title="3. Problem, Çözüm ve Sonuç" hasError={flowHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>Tespit Edilen Problem</label>
              <textarea value={problemDescription} onChange={(e) => markDirty(setProblemDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.problemDescription} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Uygulanan Çözüm</label>
              <textarea value={solutionDescription} onChange={(e) => markDirty(setSolutionDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.solutionDescription} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Elde Edilen Sonuç</label>
              <textarea value={resultDescription} onChange={(e) => markDirty(setResultDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
            </div>
          </Section>

          <Section title="4. Maddi Kazanç" defaultOpen={false}>
            <div>
              <label className={labelClass} style={labelStyle}>Maddi Kazanç Var mı?</label>
              <select value={financialGainStatus} onChange={(e) => markDirty(setFinancialGainStatus)(e.target.value as FinancialGainStatus)} className={fieldClass} style={fieldStyle}>
                {(Object.entries(FINANCIAL_STATUS_LABELS) as [FinancialGainStatus, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            {financialGainStatus === "yes" && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className={labelClass} style={labelStyle}>Kazanç Tutarı</label>
                    <input type="number" value={gainAmount} onChange={(e) => markDirty(setGainAmount)(e.target.value)} className={fieldClass} style={fieldStyle} />
                  </div>
                  <div>
                    <label className={labelClass} style={labelStyle}>Para Birimi</label>
                    <select value={currency} onChange={(e) => markDirty(setCurrency)(e.target.value as ContributionCurrency)} className={fieldClass} style={fieldStyle}>
                      <option value="TRY">TRY</option>
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className={labelClass} style={labelStyle}>Kazanç Periyodu</label>
                  <select value={gainPeriod} onChange={(e) => markDirty(setGainPeriod)(e.target.value as GainPeriod)} className={fieldClass} style={fieldStyle}>
                    <option value="">Seçiniz</option>
                    {(Object.entries(GAIN_PERIOD_LABELS) as [GainPeriod, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
              </>
            )}
          </Section>

          <Section title="5. Zamandan Kazanç" defaultOpen={false}>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Önceki İşlem Süresi</label>
                <input type="number" value={previousDuration} onChange={(e) => markDirty(setPreviousDuration)(e.target.value)} className={fieldClass} style={fieldStyle} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Yeni İşlem Süresi</label>
                <input type="number" value={newDuration} onChange={(e) => markDirty(setNewDuration)(e.target.value)} className={fieldClass} style={fieldStyle} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Süre Birimi</label>
                <select value={durationUnit} onChange={(e) => markDirty(setDurationUnit)(e.target.value as ContributionTimeUnit)} className={fieldClass} style={fieldStyle}>
                  {(Object.entries(TIME_UNIT_LABELS) as [ContributionTimeUnit, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>

            {newDurationInvalid && (
              <p className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--status-neutral)" }}>
                <TriangleAlert size={13} strokeWidth={2.5} />
                Yeni işlem süresi öncekinden büyük veya eşit olduğu için kazanç hesaplanamıyor.
              </p>
            )}

            <div>
              <label className={labelClass} style={labelStyle}>Tekrar Periyodu</label>
              <select value={repeatPeriod} onChange={(e) => markDirty(setRepeatPeriod)(e.target.value as RepeatPeriod)} className={fieldClass} style={fieldStyle}>
                <option value="">Seçiniz</option>
                {(Object.entries(REPEAT_PERIOD_LABELS) as [RepeatPeriod, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            {(perOccurrenceSaving != null || monthlyTotal != null) && (
              <div className="rounded-md p-3 text-[13px]" style={{ background: "var(--page-bg)" }}>
                {perOccurrenceSaving != null && <p>İşlem başına kazanç: <strong>{perOccurrenceSaving} {TIME_UNIT_LABELS[durationUnit].toLowerCase()}</strong></p>}
                {monthlyTotal != null && <p>Tahmini aylık toplam zaman kazancı: <strong>{formatMinutes(monthlyTotal)}</strong></p>}
              </div>
            )}
          </Section>

          <Section title="6. Diğer Kazanımlar" defaultOpen={false}>
            {gains.map((gain, i) => {
              const { amount, percent } = computeChange(gain.previousValue ?? null, gain.nextValue ?? null);
              return (
                <div key={i} className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>Kazanım {i + 1}</span>
                    <button type="button" onClick={() => removeGain(i)} style={{ color: "var(--text-muted)" }}>
                      <Trash2 size={14} strokeWidth={2} />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelClass} style={labelStyle}>Kazanım Türü</label>
                      <select value={gain.gainType} onChange={(e) => updateGain(i, { gainType: e.target.value as OtherGainType })} className={fieldClass} style={fieldStyle}>
                        {(Object.entries(GAIN_TYPE_LABELS) as [OtherGainType, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Ölçüm Birimi</label>
                      <input value={gain.unit ?? ""} onChange={(e) => updateGain(i, { unit: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                    {gain.gainType === "other" && (
                      <div className="col-span-2">
                        <label className={labelClass} style={labelStyle}>Türü Açıklayın</label>
                        <input value={gain.gainTypeOtherNote ?? ""} onChange={(e) => updateGain(i, { gainTypeOtherNote: e.target.value })} className={fieldClass} style={fieldStyle} />
                      </div>
                    )}
                    <div>
                      <label className={labelClass} style={labelStyle}>Önceki Değer</label>
                      <input type="number" value={gain.previousValue ?? ""} onChange={(e) => updateGain(i, { previousValue: e.target.value === "" ? undefined : Number(e.target.value) })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Sonraki Değer</label>
                      <input type="number" value={gain.nextValue ?? ""} onChange={(e) => updateGain(i, { nextValue: e.target.value === "" ? undefined : Number(e.target.value) })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Ölçüm Dönemi</label>
                      <input value={gain.measurementPeriod ?? ""} onChange={(e) => updateGain(i, { measurementPeriod: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div className="col-span-2">
                      <label className={labelClass} style={labelStyle}>Açıklama</label>
                      <input value={gain.description ?? ""} onChange={(e) => updateGain(i, { description: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                  </div>
                  {(amount != null || percent != null) && (
                    <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      Değişim: {amount} {percent != null && `(%${percent})`}
                    </p>
                  )}
                </div>
              );
            })}
            <button
              type="button"
              onClick={addGain}
              className="flex items-center justify-center gap-1.5 rounded-md py-2 text-xs font-medium"
              style={{ border: "1px dashed var(--border-strong)", color: "var(--accent)" }}
            >
              <Plus size={13} strokeWidth={2.5} />
              Kazanım Ekle
            </button>
          </Section>

          <Section title="7. Sınıflandırma" defaultOpen={false}>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isStandardized} onChange={(e) => markDirty(setIsStandardized)(e.target.checked)} />
              Standartlaştırıldı mı?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isApplicableOtherPlants} onChange={(e) => markDirty(setIsApplicableOtherPlants)(e.target.checked)} />
              Başka tesislerde uygulanabilir mi?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isPermanentSolution} onChange={(e) => markDirty(setIsPermanentSolution)(e.target.checked)} />
              Kalıcı çözüm mü?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={workInstructionUpdated} onChange={(e) => markDirty(setWorkInstructionUpdated)(e.target.checked)} />
              İş talimatı güncellendi mi?
            </label>
          </Section>

          {error && <p className="text-xs font-medium" style={{ color: "var(--status-negative)" }}>{error}</p>}
        </div>

        <div className="flex items-center justify-end gap-2 border-t px-5 py-3" style={{ borderColor: "var(--border)" }}>
          <button
            type="button"
            disabled={isPending || !title}
            onClick={() => handleSubmit("draft")}
            className="rounded-md px-4 py-2 text-[13px] font-medium disabled:opacity-50"
            style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
          >
            {isPending ? "Kaydediliyor..." : "Taslak Olarak Kaydet"}
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => handleSubmit("published")}
            className="rounded-md px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {isPending ? "Kaydediliyor..." : "Kaydet ve Yayımla"}
          </button>
        </div>
      </div>
    </div>
  );
}
