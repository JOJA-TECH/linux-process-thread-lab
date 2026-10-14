#!/usr/bin/env python3
"""plots.py - Genera figuras SVG (sin dependencias) a partir de mediciones.csv.

Salidas en figuras/:
  tiempo_vs_hilos.svg   - tiempo medio de pared vs numero de hilos/procesos
  cpu_vs_hilos.svg      - utilizacion media de CPU vs numero de hilos/procesos
  speedup_vs_hilos.svg  - aceleracion (speedup) vs numero de hilos/procesos
"""
import csv
import statistics as st
from collections import defaultdict

CSV_IN = "resultados/mediciones.csv"
FIG = "figuras"

W, H = 860, 560
ML, MR, MT, MB = 90, 190, 60, 70          # margenes izq/der/arr/aba
PW, PH = W - ML - MR, H - MT - MB         # area de trazado

groups = defaultdict(list)
util = defaultdict(list)
with open(CSV_IN, newline="") as f:
    for row in csv.DictReader(f):
        groups[(row["mode"], int(row["units"]))].append(float(row["wall_s"]))
        util[(row["mode"], int(row["units"]))].append(float(row["util_pct"]))

base = st.mean(groups[("secuencial", 1)])


def series(mode):
    xs, ys, lo, hi = [], [], [], []
    for (m, u), v in sorted(groups.items()):
        if m == mode:
            xs.append(u); ys.append(st.mean(v)); lo.append(min(v)); hi.append(max(v))
    return xs, ys, lo, hi


def sx(x, xmax): return ML + (x / xmax) * PW
def sy(y, ymax): return MT + PH - (y / ymax) * PH
def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;")


def chart(fname, title, ymax, ylab, series_defs, ideal=False, ideal_label="", ystep=1.0):
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">')
    p.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    p.append(f'<text x="{W/2}" y="32" font-size="20" text-anchor="middle" font-weight="bold">{esc(title)}</text>')
    xmax = 17
    # rejilla + ejes
    gy = 0.0
    while gy <= ymax + 1e-9:
        yy = sy(gy, ymax)
        lab = f"{gy:g}"
        p.append(f'<line x1="{ML}" y1="{yy:.1f}" x2="{ML+PW}" y2="{yy:.1f}" stroke="#e6e6e6"/>')
        p.append(f'<text x="{ML-10}" y="{yy+4:.1f}" font-size="12" text-anchor="end">{lab}</text>')
        gy += ystep
    for gx in [1, 2, 4, 6, 8, 10, 12, 14, 16]:
        xx = sx(gx, xmax)
        p.append(f'<line x1="{xx:.1f}" y1="{MT}" x2="{xx:.1f}" y2="{MT+PH}" stroke="#f0f0f0"/>')
        p.append(f'<text x="{xx:.1f}" y="{MT+PH+20}" font-size="12" text-anchor="middle">{gx}</text>')
    p.append(f'<line x1="{ML}" y1="{MT}" x2="{ML}" y2="{MT+PH}" stroke="#333"/>')
    p.append(f'<line x1="{ML}" y1="{MT+PH}" x2="{ML+PW}" y2="{MT+PH}" stroke="#333"/>')
    p.append(f'<text x="{ML+PW/2:.0f}" y="{H-24}" font-size="14" text-anchor="middle">'
             f'Numero de hilos / procesos (unidades)</text>')
    p.append(f'<text x="22" y="{MT+PH/2:.0f}" font-size="14" text-anchor="middle" '
             f'transform="rotate(-90 22 {MT+PH/2:.0f})">{esc(ylab)}</text>')
    if ideal:
        p.append(f'<line x1="{sx(0,xmax):.1f}" y1="{sy(0,ymax):.1f}" '
                 f'x2="{sx(xmax,ymax if ymax>=xmax else xmax):.1f}" y2="'
                 f'{sy(min(xmax,ymax),ymax):.1f}" stroke="#bbb" stroke-dasharray="6 4"/>')
    colors = {"hilos_pthread": "#1f77b4", "procesos_fork": "#d62728"}
    for mode, label in series_defs:
        xs, ys, lo, hi = series(mode)
        col = colors.get(mode, "#2ca02c")
        pts = " ".join(f"{sx(x,xmax):.1f},{sy(y,ymax):.1f}" for x, y in zip(xs, ys))
        p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        for x, y, l, h in zip(xs, ys, lo, hi):
            if h - l > 1e-9:
                p.append(f'<line x1="{sx(x,xmax):.1f}" y1="{sy(l,ymax):.1f}" '
                         f'x2="{sx(x,xmax):.1f}" y2="{sy(h,ymax):.1f}" stroke="{col}" stroke-width="1.5"/>')
            p.append(f'<circle cx="{sx(x,xmax):.1f}" cy="{sy(y,ymax):.1f}" r="3.5" fill="{col}"/>')
    if ideal:
        p.append(f'<line x1="{ML+PW-3:.1f}" y1="{MT+20}" x2="{ML+PW-40:.1f}" y2="{MT+20}" '
                 f'stroke="#bbb" stroke-dasharray="6 4" stroke-width="2"/>')
        p.append(f'<text x="{ML+PW-46:.1f}" y="{MT+24}" font-size="12" text-anchor="end">{esc(ideal_label)}</text>')
    # leyenda
    ly = MT + 20
    for mode, label in series_defs:
        col = colors.get(mode, "#2ca02c")
        p.append(f'<line x1="{ML+PW+18}" y1="{ly}" x2="{ML+PW+48}" y2="{ly}" stroke="{col}" stroke-width="2.5"/>')
        p.append(f'<text x="{ML+PW+56}" y="{ly+4}" font-size="13">{esc(label)}</text>')
        ly += 26
    p.append('</svg>')
    with open(f"{FIG}/{fname}", "w") as f:
        f.write("\n".join(p))
    print("escrito", f"{FIG}/{fname}")


series_defs = [("hilos_pthread", "Hilos pthread"), ("procesos_fork", "Procesos fork")]

ymax_t = 3.0
chart("tiempo_vs_hilos.svg", "Tiempo de pared medio vs numero de unidades",
      ymax_t, "Tiempo (s)", series_defs, ystep=0.5)
chart("cpu_vs_hilos.svg", "Utilizacion media de CPU vs numero de unidades",
      1000, "CPU utilizada (%)", series_defs, ystep=100)
chart("speedup_vs_hilos.svg", "Aceleracion vs numero de unidades (base = secuencial)",
      16, "Speedup (T1/Tn)", series_defs, ideal=True, ideal_label="ideal lineal", ystep=2)
