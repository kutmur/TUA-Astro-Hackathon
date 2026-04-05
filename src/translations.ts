export const translations = {
  tr: {
    // Hero Section
    heroTag: "TUA Astro Hackathon 2026",
    heroTitle: "4 Boyutlu Maliyet Modeli ile en uygun",
    heroTitleHighlight: "Ay rotalarını oluşturun.",
    heroDesc: "Haworth kraterinde Ay aracı rota planlaması için gerçek DEM tabanlı, çok amaçlı A* navigasyon ardışık düzeni.",
    viewGithub: "GitHub'ı İncele",
    runSimulation: "Simülasyonu Başlat",

    // 4D Cost Model Section
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

    // Impact Findings Section
    impactTitle: "Milyonlarca Dolar Tasarruf Edildi.",
    impactDesc: "Regolit sürtünmesini ve gölge risklerini tahmin ederek araçtaki aşınma, yıpranma ve termal bozulmayı en aza indiriyoruz. Sadece en kısa mesafe algoritmalarının ötesine geçerek, görev için hazır ve yorumlanabilir alternatifler sunmak amacıyla gerçek krater topografyasını kullanarak Ay rotalarını optimize ettik.",
    impactRiskTitle: "%37 Daha Düşük Görev Riski",
    impactRiskDesc: "Dengeli rota, basit en kısa yol planlamasına kıyasla yüksek eğimli ve gölgeli bölgelerden kaçınır.",
    impactEnergyTitle: "%28 Enerji Tasarrufu",
    impactEnergyDesc: "Eğim farkındalıklı maliyet, gereksiz yokuş çıkışlarını azaltarak her görev ayağı için aracın pil ömrünü uzatır.",
    impactActionTitle: "3 Eyleme Geçirilebilir Strateji",
    impactActionDesc: "Jüri/görev planlamacıları tek bir kara kutu cevabı yerine yorumlanabilir alternatifler elde ederler.",

    // Mission Profiles Section
    profileTitle: "Görev Profilleri Yapılandırması",
    profileDesc: "Uyarlanabilir planlama için parametre ağırlık dağılımlarını karşılaştırın.",
    profOptimalName: "Optimal Yol (Dengeli 4D)",
    profOptimalDesc: "Güvenli geçiş hızlarına öncelik veren optimal görev takası.",
    profShortestName: "En Kısa Mesafe",
    profShortestDesc: "Ciddi eğimleri dikkate almayan agresif, yüksek hızlı profil.",
    profThermalName: "Termal Güvenli",
    profThermalDesc: "Gölgelerden ve yüksek termal döngü risklerinden kesinlikle kaçınır.",

    // Simulation Status
    simStatusLabel: "Simülasyon Durumu:",
    simInit: "Sistem Başlatılıyor...",
    simLoaded: "DEM Yüklendi [HAWORTH]",
    simAcquired: "Ara Noktalar Alındı",
    simComputing: "Rotalar Hesaplanıyor...",
    simOptimized: "Yol Optimize Edildi ✓",
    simIdle: "Bekleniyor...",
    simRecalculating: "A* Yolu Yeniden Hesaplanıyor...",

    // Cost Label
    costLabel: "Maliyet",

    // Mission Control Panel (NEW)
    missionControlTitle: "Görev Ağırlık Kontrolü",
    missionControlDesc: "Parametreleri ayarlayın veya hazır profil seçin",
    liveCostPreview: "Canlı Maliyet Tahmini",
    customProfile: "Özel",

    // Simulation Visualizer (NEW)
    simulatorTitle: "Simülasyon Görselleştirici",
    simulatorSubtitle: "Haworth Krateri - Güney Kutbu",
    radarSweep: "Radar Taraması",
    pathAnalysis: "Yol Analizi",
    terrainMapping: "Arazi Haritalama",
    clickToStart: "Simülasyonu başlatmak için tıklayın",
    recalculatingPath: "A* Yolu Yeniden Hesaplanıyor",
    analysisComplete: "Analiz Tamamlandı",
    optimalRouteFound: "Optimal Rota Bulundu",
    processingNodes: "Düğümler işleniyor...",
    evaluatingCost: "Maliyet fonksiyonu değerlendiriliyor...",
    totalNodes: "Toplam Düğüm",
    pathLength: "Yol Uzunluğu",
    computeTime: "Hesaplama Süresi",

    // Dashboard Section (NEW)
    dashboardTitle: "Görev Kontrol Merkezi",
    dashboardDesc: "Gerçek zamanlı rota optimizasyonu ve simülasyon kontrolü",

    // Team Section (NEW)
    teamTitle: "Görev Uzmanları",
    teamDesc: "Threshold AI ekibinin arkasındaki beyinler",
    teamRole1: "Proje Lideri & Algoritma Mimarı",
    teamRole2: "Frontend Geliştirici & UI/UX Tasarımcı",
    teamRole3: "Veri Mühendisi & Backend Geliştirici",

    // Footer
    footerText: "ThresholdAI © 2026 TUA Astro Hackathon",
  },
  en: {
    // Hero Section
    heroTag: "TUA Astro Hackathon 2026",
    heroTitle: "Build optimal lunar routes with a",
    heroTitleHighlight: "4D Cost Model.",
    heroDesc: "Real DEM-based, multi-objective A* navigation pipeline for lunar rover route planning on the Haworth crater.",
    viewGithub: "View GitHub",
    runSimulation: "Run Simulation",

    // 4D Cost Model Section
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

    // Impact Findings Section
    impactTitle: "Millions of Dollars Saved.",
    impactDesc: "Minimizing rover wear-and-tear and thermal degradation by predicting regolith friction and shadow risks. We optimized lunar routes using real crater topography, moving beyond simple shortest-distance algorithms to deliver interpretable, mission-ready alternatives.",
    impactRiskTitle: "37% Lower Mission Risk",
    impactRiskDesc: "Balanced route avoids high-slope and shadow zones compared to naive shortest-path planning.",
    impactEnergyTitle: "28% Energy Savings",
    impactEnergyDesc: "Slope-aware cost reduces unnecessary uphill climbs, extending rover battery life per mission leg.",
    impactActionTitle: "3 Actionable Strategies",
    impactActionDesc: "Jury/mission planners get interpretable alternatives, not a black-box single answer.",

    // Mission Profiles Section
    profileTitle: "Mission Profiles Config",
    profileDesc: "Compare parameter weight distributions for adaptive planning.",
    profOptimalName: "Optimal Path (Balanced 4D)",
    profOptimalDesc: "Optimal mission trade-off prioritizing safe traversal speeds.",
    profShortestName: "Shortest Distance",
    profShortestDesc: "Aggressive, high-speed profile ignoring severe inclines.",
    profThermalName: "Thermal Safe",
    profThermalDesc: "Strictly avoids shadows and high thermal cycling risks.",

    // Simulation Status
    simStatusLabel: "Simulation Status:",
    simInit: "INITIALIZING SYS...",
    simLoaded: "DEM LOADED [HAWORTH]",
    simAcquired: "WAYPOINTS ACQUIRED",
    simComputing: "COMPUTING ROUTES...",
    simOptimized: "PATH OPTIMIZED ✓",
    simIdle: "STANDING BY...",
    simRecalculating: "RECALCULATING A* PATH...",

    // Cost Label
    costLabel: "Cost",

    // Mission Control Panel (NEW)
    missionControlTitle: "Mission Weight Control",
    missionControlDesc: "Adjust parameters or select a preset profile",
    liveCostPreview: "Live Cost Preview",
    customProfile: "Custom",

    // Simulation Visualizer (NEW)
    simulatorTitle: "Simulation Visualizer",
    simulatorSubtitle: "Haworth Crater - South Pole",
    radarSweep: "Radar Sweep",
    pathAnalysis: "Path Analysis",
    terrainMapping: "Terrain Mapping",
    clickToStart: "Click to start simulation",
    recalculatingPath: "Recalculating A* Path",
    analysisComplete: "Analysis Complete",
    optimalRouteFound: "Optimal Route Found",
    processingNodes: "Processing nodes...",
    evaluatingCost: "Evaluating cost function...",
    totalNodes: "Total Nodes",
    pathLength: "Path Length",
    computeTime: "Compute Time",

    // Dashboard Section (NEW)
    dashboardTitle: "Mission Control Center",
    dashboardDesc: "Real-time route optimization and simulation control",

    // Team Section (NEW)
    teamTitle: "Mission Specialists",
    teamDesc: "The minds behind Threshold AI",
    teamRole1: "Project Lead & Algorithm Architect",
    teamRole2: "Frontend Developer & UI/UX Designer",
    teamRole3: "Data Engineer & Backend Developer",

    // Footer
    footerText: "ThresholdAI © 2026 TUA Astro Hackathon",
  }
};

export type Language = 'tr' | 'en';
export type TranslationKey = keyof typeof translations.en;
