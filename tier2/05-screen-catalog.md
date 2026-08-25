# Ekran Kataloğu

`frontend/src/App.tsx`, React Router v7 route envanterinin source of truth'udur.
OIDC kimliği olmayan kullanıcı korumalı route'lardan `/login` ekranına
yönlendirilir.

| Ekran | Route | Başlıca içerik |
|---|---|---|
| SSO Giriş | `/login` | OIDC yönlendirmesi ve config/auth hata durumu |
| OIDC Callback | `/auth/callback` | Authorization Code + PKCE callback ve hedef route'a dönüş |
| Genel Bakış | `/` | Genel skor, altı KPI, tesis/formen sıralaması, performans liderleri, vardiya ve trend |
| Tesisler | `/plants` | Arama, sıralama, filtre, skor/seviye/güvenilirlik |
| Tesis Detayı | `/plants/:plantId` | KPI radar/sonuçları, vardiya karşılaştırması, şef ve formen listeleri |
| Gruplar | `/groups` | Şef/grup listesi, kapsam ve performans |
| Şef / Grup Detayı | `/groups/:chiefId` | KPI sonuçları, trend, formen comparison matrisi |
| Formenler | `/foremen` | Arama, kapsam, seviye/outstanding, skor ve sıralama |
| Formen Detayı | `/foremen/:foremanId` | Profil, tesis breakdown'u, altı KPI, trend, katkı bonusu ve aylık raporlar |
| Aylık Formen Raporu | `/foremen/:foremanId/reports/:year/:month` | Aylık snapshot, atama dönemleri, KPI ve PDF erişimi |
| KPI Analizi | `/kpis` | KPI tanımı, tesis/vardiya/formen breakdown ve sıralamalar |
| Operational Impact+ | `/improvement-works` | Katkı çalışması listesi, filtre, oluşturma/düzenleme |
| Operational Impact+ Detayı | `/improvement-works/:workId` | Problem–çözüm–sonuç, kapsam, puan, kazanım ve PDF |
| Tespitler | `/anomalies` | Özet, severity/status/analysis ve organizasyon filtreleri |
| Tespit Detayı | `/anomalies/:anomalyId` | KPI trendi, bağlam, nedenler, benzer tespitler ve AI analizi |
| Vardiya Analizi | `/shift-analysis` | Tamamlanmış ay kartları, heatmap ve filtreler |
| Vardiya Detayı | `/shifts/:shiftId` | KPI ve formen bazlı vardiya performansı |
| Yönetici Özeti | `/executive-summary` | Yıllık lider, güçlü/gelişim KPI'ları ve formen dağılımı |
| Raporlar | `/reports` | CSV/XLSX/PDF üretimi, geçmiş ve indirme |

Sol navigasyon etiketi ve grupları `frontend/src/components/Layout.tsx`
içindedir. Yönetici Özeti ayrı route'tur; ana navigasyonda bağımsız menü öğesi
olması zorunlu değildir.

Global `FilterBar`/`useFilters`; tarih, fabrika, tesis, şef, vardiya, KPI ve
formen kapsamını URL query parametrelerinde tutar. Operational Impact+,
Tespitler ve Vardiya Analizi kendi route'a özgü URL filtrelerini kullanır.
Cursor listelerinde “daha fazla yükle” yaklaşımı public pagination contract'ına
uyarlanır.

Vardiya davranışı V1 `07:00–19:00`, V2 `19:00–07:00` ve haftalık rotasyon
mantığıyla sunulur. V2'nin geceyi aşması backend tarih aralığı ve
`Europe/Istanbul` iş günü davranışıyla uyumludur.

Frontend veri katmanı `frontend/src/api/` altında Axios, TanStack Query hook'ları ve
TypeScript contract'larını barındırır. Backend'in `{data, pagination}` public
envelope'u client adapter tarafından bileşenlerin kullandığı internal yapıya
dönüştürülebilir; bu internal temsil public API contract değildir.

Production build non-root Nginx üzerinde `:8080`'de çalışır. `/api/`
`BACKEND_UPSTREAM` değerine proxy'lenir; OIDC ayarları image içine gömülmez,
container başlangıcında `/config.js` olarak render edilir.

`frontend/scripts/smoke_test_*.mjs` dosyaları package.json test runner'ına veya
CI'a bağlı resmî bir suite değildir. Developer-specific absolute path içeren
untracked betikler portable hale getirilmeden production Git staging'e
alınmamalıdır.
