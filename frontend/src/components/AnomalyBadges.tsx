import {
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Clock,
  Info,
  ListTree,
  Loader2,
  Search,
  Ban,
  XCircle,
} from "lucide-react";
import type { AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus } from "../api/types";

// Not: renkler Badge'in `${color}NN` hex-alfa birleştirmesiyle (bg/border
// opaklığı) kullanıldığından literal hex olmalı — CSS custom property burada
// geçerli değil. Değerler RENK SEMANTİĞİ'ndeki merkezi status paletiyle eşleşir.
export const SEVERITY_CONFIG: Record<AnomalySeverity, { label: string; color: string; icon: typeof Info }> = {
  low: { label: "Düşük", color: "#9ca3af", icon: Info },
  medium: { label: "Orta", color: "#1d4ed8", icon: AlertCircle },
  high: { label: "Yüksek", color: "#ca8a04", icon: AlertTriangle },
  critical: { label: "Kritik", color: "#e90128", icon: AlertOctagon },
};

// Not: renkler Badge'in `${color}NN` hex-alfa birleştirmesiyle kullanıldığından
// literal hex olmalı (bkz. SEVERITY_CONFIG notu). Değerler merkezi status
// paletiyle eşleşir; "action_pending" da in_review ile aynı attention/neutral
// tonunu paylaşır (gerçek ayrım icon+etiketle sağlanır — 3 status hue'suna
// mecburen 5 gerçek durum eşleniyor).
export const STATUS_CONFIG: Record<AnomalyStatus, { label: string; color: string; icon: typeof Info }> = {
  new: { label: "Yeni", color: "#1d4ed8", icon: CircleDot },
  in_review: { label: "İnceleniyor", color: "#ca8a04", icon: Search },
  action_pending: { label: "Aksiyon Bekliyor", color: "#ca8a04", icon: AlertTriangle },
  resolved: { label: "Çözüldü", color: "#15803d", icon: CheckCircle2 },
  closed: { label: "Kapatıldı", color: "#9ca3af", icon: XCircle },
};

export const ANALYSIS_STATUS_CONFIG: Record<AnomalyAnalysisStatus, { label: string; color: string; icon: typeof Info }> = {
  not_analyzed: { label: "Analiz Edilmedi", color: "#9ca3af", icon: Info },
  analyzing: { label: "Analiz Ediliyor", color: "#1d4ed8", icon: Loader2 },
  queued: { label: "Sırada", color: "#9ca3af", icon: Clock },
  planning: { label: "Analiz Planlanıyor", color: "#1d4ed8", icon: ListTree },
  collecting_data: { label: "Veriler Toplanıyor", color: "#1d4ed8", icon: Loader2 },
  generating_analysis: { label: "Sonuç Hazırlanıyor", color: "#1d4ed8", icon: Loader2 },
  completed: { label: "Analiz Tamamlandı", color: "#15803d", icon: CheckCircle2 },
  completed_with_warnings: { label: "Uyarılarla Tamamlandı", color: "#ca8a04", icon: AlertTriangle },
  failed: { label: "Analiz Başarısız", color: "#e90128", icon: XCircle },
  timed_out: { label: "Zaman Aşımına Uğradı", color: "#e90128", icon: Clock },
  cancelled: { label: "İptal Edildi", color: "#9ca3af", icon: Ban },
};

const _SPINNING_STATUSES = new Set(["analyzing", "collecting_data", "generating_analysis"]);

function Badge({ label, color, Icon, spin }: { label: string; color: string; Icon: typeof Info; spin?: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium"
      style={{ background: `${color}14`, color, border: `1px solid ${color}33` }}
    >
      <Icon size={12} strokeWidth={2} className={spin ? "animate-spin" : undefined} />
      {label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: AnomalySeverity }) {
  const c = SEVERITY_CONFIG[severity];
  return <Badge label={c.label} color={c.color} Icon={c.icon} />;
}

export function StatusBadge({ status }: { status: AnomalyStatus }) {
  const c = STATUS_CONFIG[status];
  return <Badge label={c.label} color={c.color} Icon={c.icon} />;
}

export function AnalysisStatusBadge({ status }: { status: AnomalyAnalysisStatus }) {
  const c = ANALYSIS_STATUS_CONFIG[status];
  return <Badge label={c.label} color={c.color} Icon={c.icon} spin={_SPINNING_STATUSES.has(status)} />;
}
