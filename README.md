# TUA Astro Hackathon - Lunar Route Optimization

Real-DEM-based, multi-objective A* navigation pipeline for lunar rover route planning.

This project plans and visualizes rover routes on the Haworth crater terrain by combining:
- distance efficiency,
- slope safety,
- regolith/friction risk,
- shadow/thermal risk.

The result is a clear, explainable route analysis suitable for technical demo and jury presentation.

## Demo (Input / Output)

### Input
![Input](input.png)

### Output
![Output](output.png)

## Why This Project Matters

- Uses **real lunar elevation data** (GeoTIFF DEM), not synthetic toy maps.
- Runs **true 8-connected A*** over terrain-aware cost layers.
- Produces **three mission profiles** for decision support, not a single black-box path.
- Generates **presentation-ready visuals** with clear A/B markers, route overlays, and cumulative costs.

## AYAP-2 4D Cost Model

Each move cost is computed as:

```text
C_total = [ (W_d * D) + (W_e * E) + (W_s * S) + (W_g * G) ] * 1000
```

Where:
- `D`: Euclidean distance between grid cells.
- `E`: Asymmetric slope cost (steep uphill penalty, mild downhill reward).
- `S`: Surface friction/regolith roughness proxy.
- `G`: Shadow/thermal risk proxy (hillshade + lowland depth).

## Route Profiles

| Profile | W_d | W_e | W_s | W_g | Intent |
|---|---:|---:|---:|---:|---|
| Optimal Path (Balanced 4D) | 1.4 | 4.0 | 1.6 | 0.22 | Balanced mission trade-off |
| Shortest Distance | 9.5 | 0.25 | 0.05 | 0.01 | Distance-priority, aggressive |
| Thermal Safe | 0.9 | 1.2 | 0.5 | 6.5 | Avoid shadow/thermal risk |

## Project Structure

```text
.
|-- ayap2_nav/
|   |-- main.py            # Recommended jury/demo entry point
|   |-- config.py          # UV points, profile weights, output names
|   |-- dem_loader.py      # GeoTIFF loading + E/S/G cost-layer generation
|   |-- planner.py         # 8-direction A* search engine
|   `-- visualization.py   # 3-step high-quality figure generation
|-- src/
|   |-- ayap2_astar_routes.py  # Alternative single-script route pipeline
|   |-- plot.py                # Direct DEM plot helper
|   `-- main.py                # Generic pipeline skeleton
|-- data/
|   `-- haworth_crater_DEM_1m.tif
`-- README.md
```

## Setup

### Requirements

- Python 3.10+
- `numpy`
- `matplotlib`
- `rasterio`

Optional:
- `opencv-python` (only needed when using image-based DEM input in `src/ayap2_astar_routes.py`).

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy matplotlib rasterio
```

## Quick Start (Recommended)

Run the full 3-step AYAP-2 pipeline:

```bash
python3 ayap2_nav/main.py
```

Custom output directory:

```bash
python3 ayap2_nav/main.py --output-dir ./output
```

Custom DEM path:

```bash
python3 ayap2_nav/main.py --tif ./data/haworth_crater_DEM_1m.tif
```

Control crop/downsample:

```bash
python3 ayap2_nav/main.py --window-size 1500 --downsample 1
```

## Generated Files

For the current submission/demo, we use two PNG files:
- `input.png`
- `output.png`

If you run `ayap2_nav/main.py`, detailed analysis figures are still generated in the chosen `--output-dir`.

## Alternative Entry Points

### A) Single-Script A* + Plot

```bash
python3 src/ayap2_astar_routes.py --dem-tif ./data/haworth_crater_DEM_1m.tif --save output.png
```

Headless run:

```bash
python3 src/ayap2_astar_routes.py --dem-tif ./data/haworth_crater_DEM_1m.tif --save output.png --no-show
```

### B) Direct DEM Visualization

```bash
python3 src/plot.py --tif-path ./data/haworth_crater_DEM_1m.tif --save-annotated input.png --no-show
```

### C) Generic Planning Skeleton

```bash
python3 src/main.py --no-plot
```

Note: `src/main.py --run-planner` requires implementing `user_cost_formula` first.

## Technical Notes

- The loader guards against overly aggressive downsampling using a minimum grid size policy.
- Invalid/nodata elevations are sanitized before planning.
- Route overlays are z-lifted to stay visible above terrain.
- Marker poles are anchored to real surface cells for clear spatial interpretation.

## Jury Talking Points (Ready-to-Pitch)

- We optimize lunar routes with a **multi-objective 4D mission cost**, not only shortest distance.
- We use **real crater topography** and derive physically meaningful risk proxies.
- We deliver **interpretable alternatives** for mission strategy (balanced, shortest, thermal-safe).
- We provide **high-quality visual evidence** of route behavior on terrain.

## License

MIT License - see `LICENSE`.
