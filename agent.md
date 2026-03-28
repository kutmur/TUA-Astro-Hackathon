# Otonom Navigasyon Ajanı (Lunar Rover Agent) Mimarisi

## 🎯 Ana Hedef
TUA Astro Hackathonu için "Ay Yüzeyi İçin Otonom Rota Optimizasyonu" problemine çözüm olarak; 24 saat içerisinde sağlanan küresel uydu verileriyle (DEM - Sayısal Yükseklik Modeli) Ay yüzeyi üzerinde Google Maps benzeri bir haritalama sistemi kurmak. Bu harita üzerinde otonom aracın, sadece en kısa değil, uzay şartlarında **"hayatta kalma ihtimali en yüksek (en optimum)"** yolu bulmasını D* Lite algoritması ve çok amaçlı maliyet optimizasyonu ile sağlamak.

---

## ⚠️ Temel Problemler ve Çözüm Stratejilerimiz

* **Harita Körlüğü ve Sürpriz Engeller (Çözünürlük Problemi):** Küresel uydu verileri, çözünürlük limitlerinden dolayı 30-50 cm boyutlarındaki ölümcül kayaları veya ufak kraterleri göremez. Algoritmamız, yolda karşılaşılan "sürpriz" engelleri uydu verilerinden gelen bilgiyle birlikte yazdığımız D* Lite algoritması ile tespit edip, saniyeler içinde yeni kavisler (lokal rotalar) çizecek.

* **Ay Kumu (Regolit) ve Tekerlek Patinajı (Terramekanik):** Ay yüzeyindeki ince kumda dik yamaçlara tırmanmak tekerleği kuma gömer (slip) ve bataryayı boşa harcar. Sisteme entegre edeceğimiz "Stokastik Kayma Modeli" ile eğimi sadece bir yükseklik olarak değil, bir "patinaj ve devrilme riski" olarak hesaplayacağız.

* **Sabit Güneş Panelleri ve Ölümcül Gölgeler (Hayatta Kalma Kısıtı):** AYAP-2 konseptindeki sabit güneş panelleri (-X/+X yönlü) ve Ay kutuplarındaki derin krater gölgeleri aracın donmasına yol açabilir. Rotamızı çizerken aracı sadece X, Y koordinatlarında değil; güneşe olan yönelimi (heading) ve gölgelerin zamansal değişimiyle birlikte 4 boyutlu bir denklemde hayatta tutacağız.

* **Sığ Maliyet (Cost) Fonksiyonu Problemi:** Standart navigasyonlar sadece "en kısa mesafeyi" en iyi yol sanır. Bizim Google Maps sistemimizin beyni; mesafeyi, eğim/kayma riskini ve güneşsizlik süresini matematiksel ağırlıklarla ($\alpha, \beta, \gamma$) birleştiren **"Çok Amaçlı Dinamik Maliyet Fonksiyonu"** üzerinden karar verecek. 

> **💡 Sonuç Bildirgesi:** Kısacası otonom aracımız; kısa ama ölümcül bir krater yamacı yerine, uzun ama güvenli ve güneşli platoyu seçecek.