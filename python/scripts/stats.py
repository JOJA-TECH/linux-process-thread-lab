#!/usr/bin/env python3
"""stats.py - Calcula estadisticas a partir de resultados/mediciones.csv.

Genera:
  resultados/estadisticas.csv  (datos por configuracion)
  resultados/estadisticas.md   (tabla Markdown lista para el informe)
Debe ejecutarse desde el directorio `python/`.
"""
import csv
import statistics as st
from collections import defaultdict

CSV_IN = "resultados/mediciones.csv"
CSV_OUT = "resultados/estadisticas.csv"
MD_OUT = "resultados/estadisticas.md"

groups = defaultdict(list)
cpu = defaultdict(list)
util = defaultdict(list)

with open(CSV_IN, newline="") as f:
    for row in csv.DictReader(f):
        key = (row["mode"], int(row["units"]))
        groups[key].append(float(row["wall_s"].replace(",", ".")))
        cpu[key].append(float(row["cpu_s"].replace(",", ".")))
        util[key].append(float(row["util_pct"].replace(",", ".")))

base = st.mean(groups[("secuencial", 1)])

rows = []
for (mode, units), walls in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    m = st.mean(walls)
    mn, mx = min(walls), max(walls)
    sd = st.stdev(walls) if len(walls) > 1 else 0.0
    speedup = base / m
    eff = speedup / units * 100.0
    rows.append({
        "mode": mode, "units": units, "n": len(walls),
        "mean_s": m, "min_s": mn, "max_s": mx, "range_s": mx - mn, "stdev_s": sd,
        "mean_cpu_s": st.mean(cpu[(mode, units)]),
        "mean_util_pct": st.mean(util[(mode, units)]),
        "speedup": speedup, "efficiency_pct": eff,
    })

with open(CSV_OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

with open(MD_OUT, "w") as f:
    f.write(f"Linea base (secuencial, 1 unidad): media = {base:.4f} s\n\n")
    f.write("| Modo | Unidades | n | Media (s) | Min (s) | Max (s) | Rango (s) | Desv. est. (s) | CPU media (s) | Util. media (%) | Speedup | Eficiencia (%) |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['mode']} | {r['units']} | {r['n']} | {r['mean_s']:.4f} | {r['min_s']:.4f} | "
                f"{r['max_s']:.4f} | {r['range_s']:.4f} | {r['stdev_s']:.4f} | {r['mean_cpu_s']:.4f} | "
                f"{r['mean_util_pct']:.2f} | {r['speedup']:.3f} | {r['efficiency_pct']:.1f} |\n")

print(open(MD_OUT).read())
