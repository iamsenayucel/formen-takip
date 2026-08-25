import { AlertTriangle, Info, Mail, Phone } from "lucide-react";
import { EntityHero, type EntityHeroRankItem } from "./EntityHero";
import type { ForemanDetail } from "../api/types";

function plantSequenceLabel(plantNames: string[]): string | null {
  if (plantNames.length === 0) return null;
  const numbers = plantNames.map((name) => name.replace(/\s*Tesis$/, ""));
  return `${numbers.join(", ")} Tesis`;
}

export function ForemanProfileHeader({
  foreman,
  factoryCode,
  responsiblePlants,
  shiftLabel,
  chiefName,
}: {
  foreman: ForemanDetail;
  factoryCode: string | null | undefined;
  responsiblePlants: string[];
  shiftLabel: string | null;
  chiefName: string | null;
}) {
  const rank: EntityHeroRankItem[] = [
    { label: "Şirket Sıralaması", value: `${foreman.companyRank ?? "-"} / ${foreman.companyTotal}` },
  ];
  if (foreman.plantRank !== null && foreman.plantRank !== undefined) {
    rank.push({ label: "Tesis Sıralaması", value: `${foreman.plantRank} / ${foreman.plantTotal}` });
  }

  return (
    <EntityHero
      eyebrow="Formen"
      title={foreman.fullName}
      subtitle={`Sicil No: ${foreman.employeeNumber}`}
      metaItems={[
        factoryCode,
        plantSequenceLabel(responsiblePlants),
        shiftLabel,
        chiefName ? `Şef: ${chiefName}` : null,
        `Göreve Başlama: ${foreman.hireDate}`,
      ]}
      contact={
        (foreman.phoneNumber || foreman.email) && (
          <>
            {foreman.phoneNumber && (
              <a href={`tel:${foreman.phoneNumber}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
                <Phone size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
                {foreman.phoneNumber}
              </a>
            )}
            {foreman.email && (
              <a href={`mailto:${foreman.email}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
                <Mail size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
                {foreman.email}
              </a>
            )}
          </>
        )
      }
      score={foreman.generalPerformanceScore}
      scoreMax={120}
      scoreLabel="Genel Performans Puanı"
      level={foreman.level}
      statusNote={
        !foreman.inScope
          ? { icon: Info, text: "Bu formen seçili filtrelerle eşleşmiyor", tone: "neutral" }
          : !foreman.isReliable
            ? { icon: AlertTriangle, text: "Eksik KPI verisi", tone: "attention" }
            : null
      }
      extraLines={[
        { label: "Operasyonel Performans", value: `${foreman.operationalScore.toFixed(1)} / 100` },
        { label: "Son 3 Ay Operational Impact+ Bonusu", value: `+${foreman.contributionBonus}`, tone: "positive" },
      ]}
      rank={rank}
    />
  );
}
