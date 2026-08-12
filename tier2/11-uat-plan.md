# 11. Kabul Testi (UAT) Planı

## Kullanıcı Personaları
- **Üst Yönetim (Salt Okunur)**: Sistemde veriyi manipüle edememeli, sadece analiz sayfalarını görmeli.
- **Tesis Yöneticisi**: Sadece bağlı olduğu fabrikanın verilerini ve formenlerin skorlarını görebilmeli.

## Senaryolar
1. **Giriş ve Yetkilendirme**: Başarılı login işlemi sonrasında yetkisi olmayan bir sayfaya (ör. admin paneli) erişememe.
2. **Dashboard Veri Teyidi**: Tesislerin KPI puanları, doğru ağırlıklı geometrik ortalama ile hesaplanıp gösterilmeli.
3. **AI Analizi**: Tespitler menüsünde, bir anomali seçilip "Yapay Zeka ile Analiz Et" butonuna basıldığında başarılı bir sonuç ve çıkarım döndürülmesi.
