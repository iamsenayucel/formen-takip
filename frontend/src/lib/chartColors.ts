export const CATEGORICAL_LIGHT = [
  "#2a78d6",
  "#eb6834",
  "#1baf7a",
  "#eda100",
  "#e87ba4",
  "#008300",
  "#4a3aa7",
  "#e34948",
];

export const CATEGORICAL_DARK = [
  "#3987e5",
  "#d95926",
  "#199e70",
  "#c98500",
  "#d55181",
  "#008300",
  "#9085e9",
  "#e66767",
];

export const SEQUENTIAL_BLUE = {
  100: "#cde2fb", 150: "#b7d3f6", 200: "#9ec5f4", 250: "#86b6ef",
  300: "#6da7ec", 350: "#5598e7", 400: "#3987e5", 450: "#2a78d6",
  500: "#256abf", 550: "#1c5cab", 600: "#184f95", 650: "#104281", 700: "#0d366b",
};

export const CHART_INK = {
  primary: "#0f172a", primaryDark: "#f1f5f9",
  secondary: "#475569", secondaryDark: "#94a3b8",
  muted: "#1f2937", mutedDark: "#94a3b8",
  grid: "#e2e8f0", gridDark: "#1f2937",
  axis: "#cbd5e1", axisDark: "#334155",
};

export function categoricalColor(index: number, dark = false): string {
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return palette[index % palette.length];
}

// Data visualization tonları status renklerinden bağımsızdır (bkz. RENK
// SEMANTİĞİ): mevcut dönem serisi her zaman bu "primary data" mavisini
// kullanır, tema veya performans durumu ne olursa olsun kırmızı/yeşile
// boyanmaz. Karşılaştırma/hedef serileri için bkz. DATA_SECONDARY.
export const DATA_PRIMARY = "#1c357f";
export const DATA_PRIMARY_DARK = SEQUENTIAL_BLUE[300];
export const DATA_SECONDARY = "#8586a7";
export const DATA_SECONDARY_DARK = "#9a9bbd";
// Hedef çizgisi rengi kasıtlı olarak tema bağımsızdır (index.css --data-target
// her iki temada da aynı değeri taşır) — hedef her zaman aynı nötr tonda kalır,
// karşılaştırma serisinden (DATA_SECONDARY) ayrı bir görsel kimlik taşır.
export const DATA_TARGET = "#8586a7";

export function accentLineColor(dark = false): string {
  return dark ? DATA_PRIMARY_DARK : DATA_PRIMARY;
}

export function dataSecondaryColor(dark = false): string {
  return dark ? DATA_SECONDARY_DARK : DATA_SECONDARY;
}

export function dataTargetColor(): string {
  return DATA_TARGET;
}

// Status renkleri — index.css'teki --status-* token değerleriyle birebir eşleşir.
// SVG chart prop'ları (fill/stroke) için literal hex gerekir, bu yüzden CSS
// custom property yerine burada da sabit değer olarak tutulur.
export type ChartStatusTone = "positive" | "negative" | "neutral" | "unknown";

const STATUS_COLORS: Record<ChartStatusTone, { light: string; dark: string }> = {
  positive: { light: "#15803d", dark: "#22a35e" },
  negative: { light: "#e90128", dark: "#f0435f" },
  neutral: { light: "#ca8a04", dark: "#d9a520" },
  unknown: { light: "#9ca3af", dark: "#64748b" },
};

export function statusChartColor(tone: ChartStatusTone, dark = false): string {
  return dark ? STATUS_COLORS[tone].dark : STATUS_COLORS[tone].light;
}

export function resolveChartInk(dark = false) {
  return {
    primary: dark ? CHART_INK.primaryDark : CHART_INK.primary,
    secondary: dark ? CHART_INK.secondaryDark : CHART_INK.secondary,
    muted: dark ? CHART_INK.mutedDark : CHART_INK.muted,
    grid: dark ? CHART_INK.gridDark : CHART_INK.grid,
    axis: dark ? CHART_INK.axisDark : CHART_INK.axis,
  };
}
