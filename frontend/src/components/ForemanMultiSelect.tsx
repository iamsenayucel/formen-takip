import { useMemo, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { useForemen } from "../api/hooks";
import { fieldClass, fieldStyle } from "../lib/formStyles";
import { useDismissablePopover } from "../hooks/useDismissablePopover";

export interface SelectedForeman {
  id: string;
  name: string;
}

interface Props {
  selected: SelectedForeman[];
  onChange: (selected: SelectedForeman[]) => void;
  disabled?: boolean;
}

export function ForemanMultiSelect({ selected, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const close = () => setOpen(false);
  const triggerRef = useDismissablePopover(open, close);

  const results = useForemen({ search: query || undefined }, 10);
  const resultItems = results.data?.pages.flatMap((page) => page.items) ?? [];
  const selectedIds = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);

  const toggle = (id: string, name: string) => {
    if (selectedIds.has(id)) {
      onChange(selected.filter((s) => s.id !== id));
    } else {
      onChange([...selected, { id, name }]);
    }
  };

  const remove = (id: string) => onChange(selected.filter((s) => s.id !== id));

  return (
    <div className="relative">
      {selected.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {selected.map((s) => (
            <span
              key={s.id}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
              style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
            >
              {s.name}
              {!disabled && (
                <button type="button" onClick={() => remove(s.id)} className="hover:opacity-70">
                  <X size={11} strokeWidth={2.5} />
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex w-full items-center justify-between ${fieldClass} disabled:opacity-50`}
        style={fieldStyle}
      >
        <span style={{ color: "var(--text-muted)" }}>Formen ara ve seç...</span>
        <ChevronDown size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
      </button>

      {open && !disabled && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div
            className="absolute z-20 mt-1 w-full rounded-md shadow-lg"
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
                className={fieldClass}
                style={fieldStyle}
              />
            </div>
            <div className="max-h-52 overflow-y-auto p-1">
              {results.isLoading && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>Aranıyor...</div>
              )}
              {results.data && resultItems.length === 0 && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>Eşleşen formen yok</div>
              )}
              {resultItems.map((f) => (
                <label
                  key={f.id}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-[var(--page-bg)]"
                  style={{ color: "var(--text-primary)" }}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(f.id)}
                    onChange={() => toggle(f.id, f.fullName)}
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
