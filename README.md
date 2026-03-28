# TUA-Astro-Hackathon

Ay yuzeyi rota optimizasyonu icin A* tabanli DEM planlayici.

## Hizli kullanim

Varsayilan calisma (otomatik engebeli pencere secimi acik):

```bash
python3 src/main.py
```

Hizli dry-run (plot yok):

```bash
python3 src/main.py --no-plot
```

Otomatik engebeli pencere taramasini ayarlama:

```bash
python3 src/main.py --auto-rough-window --window-size 400 --scan-step 300 --min-valid-ratio 0.7 --no-plot
```

Manuel pencere ile calisma (otomatik secim devre disi kalir):

```bash
python3 src/main.py --pixel-window 10400 10800 8000 8400 --downsample 2 --z-exaggeration 3.0
```

Harita koordinatlari ile kirpma:

```bash
python3 src/main.py --bbox XMIN YMIN XMAX YMAX --z-exaggeration 3.5
```

Notlar:

- `--pixel-window` veya `--bbox` verildiginde otomatik engebeli pencere secimi uygulanmaz.
- `--z-exaggeration` sadece 3B gorselde dikey olcegi degistirir; planlama maliyetini etkilemez.
- Ortamda `matplotlib` yoksa plot acmaya calisildiginda acik bir hata mesaji verilir.
