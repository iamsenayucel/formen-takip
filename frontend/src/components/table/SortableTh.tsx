import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { thClass, thStyle } from "../../lib/tableStyles";

// Tesisler/Gruplar/Formenler liste tablolarında ve ContributionWorkTable'da
// tekrarlanan sıralanabilir sütun başlığı — sort state/mantığı çağıranda kalır,
// bu yalnızca görsel+erişilebilirlik kalıbını paylaşır.
export function SortableTh<F extends string>({
  field,
  label,
  activeField,
  direction,
  onSort,
  align,
}: {
  field: F;
  label: string;
  activeField: F;
  direction: "asc" | "desc";
  onSort: (field: F) => void;
  align?: "right";
}) {
  const active = activeField === field;
  const Icon = active ? (direction === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th className={thClass} style={thStyle}>
      <button
        type="button"
        onClick={() => onSort(field)}
        aria-label={`${label} sütununa göre sırala${active ? `, şu an ${direction === "asc" ? "artan" : "azalan"} sırada` : ""}`}
        className={`flex items-center gap-1 uppercase tracking-wide hover:text-[var(--text-primary)] ${align === "right" ? "ml-auto" : ""}`}
        style={{ color: active ? "var(--primary)" : "inherit" }}
      >
        {label}
        <Icon size={12} strokeWidth={2} className={active ? "" : "opacity-40"} aria-hidden="true" />
      </button>
    </th>
  );
}
