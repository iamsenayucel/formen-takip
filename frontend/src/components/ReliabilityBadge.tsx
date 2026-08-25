import { AlertTriangle } from "lucide-react";

// "Veri Güvenilirliği: Tam / Eksik veri" — Formenler/Gruplar listelerinde ve
// Grup Detayı'nın ekip tablosunda tekrarlanan durum göstergesi.
export function ReliabilityBadge({ isReliable }: { isReliable: boolean }) {
  if (isReliable) {
    return <span className="text-metadata" style={{ color: "var(--text-muted)" }}>Tam</span>;
  }
  return (
    <span className="text-metadata flex items-center gap-1 font-medium" style={{ color: "var(--status-neutral)" }}>
      <AlertTriangle size={12} strokeWidth={2} />
      Eksik veri
    </span>
  );
}
