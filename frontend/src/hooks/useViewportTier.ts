import { useEffect, useState } from "react";

export type ViewportTier = "wide" | "standard" | "compact";

const STANDARD_MAX = "(max-width: 1599px)";
const COMPACT_MAX = "(max-width: 1439px)";

function computeTier(): ViewportTier {
  if (typeof window === "undefined") return "wide";
  if (window.matchMedia(COMPACT_MAX).matches) return "compact";
  if (window.matchMedia(STANDARD_MAX).matches) return "standard";
  return "wide";
}

// index.css'teki density breakpoint katmanlarıyla (1599 / 1439px) birebir eşleşir.
// Recharts axis/legend/tooltip fontSize'ları SVG üzerinde inline sayısal prop
// olarak set edildiğinden CSS custom property'lerle küçültülemez — bu hook aynı
// katman sınırlarını JS tarafında da sağlar.
export function useViewportTier(): ViewportTier {
  const [tier, setTier] = useState<ViewportTier>(computeTier);

  useEffect(() => {
    const standard = window.matchMedia(STANDARD_MAX);
    const compact = window.matchMedia(COMPACT_MAX);
    const update = () => setTier(computeTier());
    standard.addEventListener("change", update);
    compact.addEventListener("change", update);
    update();
    return () => {
      standard.removeEventListener("change", update);
      compact.removeEventListener("change", update);
    };
  }, []);

  return tier;
}
