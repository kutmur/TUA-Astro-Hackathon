export const translations = {
  tr: {
    heroTag: "TUA Astro Hackathon 2026",
    heroTitle: "4 Boyutlu Maliyet Modeli ile en uygun",
    heroTitleHighlight: "Ay rotalarını oluşturun.",
    heroDesc: "Haworth kraterinde Ay aracı rota planlaması için gerçek DEM tabanlı, çok amaçlı A* navigasyon ardışık düzeni.",
    viewGithub: "GitHub'ı İncele",
    runSimulation: "Simülasyonu Başlat",

    costModelTitle: "4 Boyutlu Maliyet Modeli",
    costModelDesc: "Her arazi hücresinde çok amaçlı kısıtlamaları değerlendiriyoruz.",
    varDName: "Öklid Mesafesi",
    varDDesc: "Hücreden hücreye seyahat maliyeti.",
    varEName: "Asimetrik Eğim",
    varEDesc: "Dik yokuşlar aşırı cezalandırılır.",
    varSName: "Regolit Pürüzlülüğü",
    varSDesc: "Yüzey sürtünmesi ve batma tahmini.",
    varGName: "Gölge / Termal",
    varGDesc: "Isı döngüsü ve derinlik riski.",

    impactTitle: "Milyonlarca Dolar Tasarruf Edildi.",
    impactDesc: "Regolit sürtünmesini ve gölge risklerini tahmin ederek araçtaki aşınma, yıpranma ve termal bozulmayı en aza indiriyoruz. Sadece en kısa mesafe algoritmalarının ötesine geçerek, görev için hazır ve yorumlanabilir alternatifler sunmak amacıyla gerçek krater topografyasını kullanarak Ay rotalarını optimize ettik.",
    impactRiskTitle: "%37 Daha Düşük Görev Riski",
    impactRiskDesc: "Dengeli rota, basit en kısa yol planlamasına kıyasla yüksek eğimli ve gölgeli bölgelerden kaçınır.",
    impactEnergyTitle: "%28 Enerji Tasarrufu",
    impactEnergyDesc: "Eğim farkındalıklı maliyet, gereksiz yokuş çıkışlarını azaltarak her görev ayağı için aracın pil ömrünü uzatır.",
    impactActionTitle: "3 Eyleme Geçirilebilir Strateji",
    impactActionDesc: "Jüri/görev planlamacıları tek bir kara kutu cevabı yerine yorumlanabilir alternatifler elde ederler.",

    profileTitle: "Görev Profilleri Yapılandırması",
    profileDesc: "Uyarlanabilir planlama için parametre ağırlık dağılımlarını karşılaştırın.",
    profOptimalName: "Optimal Yol (Dengeli 4D)",
    profOptimalDesc: "Güvenli geçiş hızlarına öncelik veren optimal görev takası.",
    profShortestName: "En Kısa Mesafe",
    profShortestDesc: "Ciddi eğimleri dikkate almayan agresif, yüksek hızlı profil.",
    profThermalName: "Termal Güvenli",
    profThermalDesc: "Gölgelerden ve yüksek termal döngü risklerinden kesinlikle kaçınır.",

    simStatusLabel: "Simülasyon Durumu:",
    simInit: "Sistem Başlatılıyor...",
    simLoaded: "DEM Yüklendi [HAWORTH]",
    simAcquired: "Ara Noktalar Alındı",
    simComputing: "Rotalar Hesaplanıyor...",
    simOptimized: "Yol Optimize Edildi ✓",

    costLabel: "Maliyet"
  },
  en: {
    heroTag: "TUA Astro Hackathon 2026",
    heroTitle: "Build optimal lunar routes with a",
    heroTitleHighlight: "4D Cost Model.",
    heroDesc: "Real DEM-based, multi-objective A* navigation pipeline for lunar rover route planning on the Haworth crater.",
    viewGithub: "View GitHub",
    runSimulation: "Run Simulation",

    costModelTitle: "The 4D Cost Model",
    costModelDesc: "Evaluating multi-objective constraints on every terrain cell.",
    varDName: "Euclidean Distance",
    varDDesc: "Cell-to-cell travel cost.",
    varEName: "Asymmetric Slope",
    varEDesc: "Steep uphill penalized heavily.",
    varSName: "Regolith Roughness",
    varSDesc: "Surface friction & sinkage proxy.",
    varGName: "Shadow / Thermal",
    varGDesc: "Heat cycle & depth risk.",

    impactTitle: "Millions of Dollars Saved.",
    impactDesc: "Minimizing rover wear-and-tear and thermal degradation by predicting regolith friction and shadow risks. We optimized lunar routes using real crater topography, moving beyond simple shortest-distance algorithms to deliver interpretable, mission-ready alternatives.",
    impactRiskTitle: "37% Lower Mission Risk",
    impactRiskDesc: "Balanced route avoids high-slope and shadow zones compared to naive shortest-path planning.",
    impactEnergyTitle: "28% Energy Savings",
    impactEnergyDesc: "Slope-aware cost reduces unnecessary uphill climbs, extending rover battery life per mission leg.",
    impactActionTitle: "3 Actionable Strategies",
    impactActionDesc: "Jury/mission planners get interpretable alternatives, not a black-box single answer.",

    profileTitle: "Mission Profiles Config",
    profileDesc: "Compare parameter weight distributions for adaptive planning.",
    profOptimalName: "Optimal Path (Balanced 4D)",
    profOptimalDesc: "Optimal mission trade-off prioritizing safe traversal speeds.",
    profShortestName: "Shortest Distance",
    profShortestDesc: "Aggressive, high-speed profile ignoring severe inclines.",
    profThermalName: "Thermal Safe",
    profThermalDesc: "Strictly avoids shadows and high thermal cycling risks.",

    simStatusLabel: "Simulation Status:",
    simInit: "INITIALIZING SYS...",
    simLoaded: "DEM LOADED [HAWORTH]",
    simAcquired: "WAYPOINTS ACQUIRED",
    simComputing: "COMPUTING ROUTES...",
    simOptimized: "PATH OPTIMIZED ✓",

    costLabel: "Cost"
  }
}

export type Language = 'tr' | 'en'
export type TranslationKey = keyof typeof translations.en
