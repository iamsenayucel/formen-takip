# Ekran Kataloğu

`frontend/src/App.tsx` React Router v7 ile sayfaları tanımlar; kimlik
doğrulaması olmayan istekler `/login`'e yönlendirilir (`ProtectedRoute`).

| Sayfa | Yol |
|---|---|
| Dashboard | `/` |
| Tesisler / Tesis Detayı | `/plants`, `/plants/:plantId` |
| Şef Grupları / Grup Detayı | `/groups`, `/groups/:chiefId` |
| Formenler / Formen Detayı | `/foremen`, `/foremen/:foremanId` |
| KPI Analizi | `/kpis` |
| Aksiyon Planları | `/action-plans` |
| Katkılar / Detay | `/improvement-works`, `/improvement-works/:workId` |
| Tespitler / Tespit Detayı | `/anomalies`, `/anomalies/:anomalyId` |
| Raporlar | `/reports` |
| Veri Kalitesi | `/data-quality` |
| Entegrasyon Durumu | `/integration-status` |
| Denetim Kayıtları | `/audit-log` |

Dizin yapısı: `api/` (axios client + TanStack Query hook'ları + tip
tanımları), `components/` (paylaşılan bileşenler ve `charts/` altında
Recharts sarmalayıcıları), `context/` (`AuthContext`, `ThemeContext`),
`hooks/useFilters.ts` (filtre durumunu URL query param'larında tutar),
`lib/` (`chartColors.ts`, `tableStyles.ts`, `formStyles.ts`), `pages/`.

Arayüz dili Türkçedir; tasarımda emoji kullanılmaz, ikonlar
`lucide-react`'ten gelir. Tema tamamen CSS custom property'leri üzerinden
çalışır (`index.css`, `:root[data-theme="dark"|"light"]`), `ThemeContext`
tarafından yönetilir ve varsayılan olarak koyu temadır (localStorage'da
kalıcı). Recharts renk/tooltip prop'ları CSS değişkeni kabul etmediği için
`lib/chartColors.ts` içindeki tema-duyarlı yardımcılar (`resolveChartInk`,
`accentLineColor`, `categoricalColor`) kullanılır.

Vite dev sunucusu (`vite.config.ts`) `:5173` portunda çalışır ve `/api`
isteklerini `http://127.0.0.1:8000`'e proxy'ler. Prod build'de statik
dosyalar Nginx ile sunulur ve `/api/` istekleri `nginx.conf` üzerinden
`http://backend:8000/api/`'ye proxy'lenir.

`frontend/scripts/*.mjs` altında Playwright ile yazılmış smoke test
betikleri bulunur (login, filtreleme, sıralama, PDF render, logo gibi
senaryolar); `frontend/` dizininden çalıştırılmalıdır (playwright oradan
çözülür).