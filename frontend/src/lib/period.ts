type PeriodParams = { date_from: string; date_to: string };

// date_from/date_to birer business date string'idir (YYYY-MM-DD, timezone-free).
// Bunları Date#setDate() ile (browser'ın kendi local saat dilimine göre) mutasyona
// uğratmak yerine tamamen UTC milisaniye ekseninde işleriz — sonuç browser'ın
// işletim sistemi saat dilimi ne olursa olsun aynı kalır.
const DAY_MS = 86_400_000;

export function previousPeriodParams<T extends PeriodParams>(params: T): T {
  const fromMs = Date.parse(`${params.date_from}T00:00:00Z`);
  const toMs = Date.parse(`${params.date_to}T00:00:00Z`);
  const periodDays = Math.round((toMs - fromMs) / DAY_MS) + 1;
  const prevToMs = fromMs - DAY_MS;
  const prevFromMs = prevToMs - (periodDays - 1) * DAY_MS;
  const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
  return { ...params, date_from: iso(prevFromMs), date_to: iso(prevToMs) };
}
