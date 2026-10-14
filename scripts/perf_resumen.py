#!/usr/bin/env python3
"""perf_resumen.py - Parsea una salida de `perf stat` y calcula IPC y tasas.

Uso:
    python3 scripts/perf_resumen.py [archivo_entrada] [archivo_salida]

Por defecto lee resultados/perf_mediciones.txt (contadores de usuario) y
escribe resultados/perf_resumen.md. Acepta tambien la salida con sudo
(eventos de kernel) para generar una tabla equivalente.
"""
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "resultados/perf_mediciones.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "resultados/perf_resumen.md"


def num(s):
    # formato es_ES: 1.234.567 -> 1234567 ; 4.116,77 -> 4116.77
    return float(s.strip().replace(".", "").replace(",", "."))


def key(name):
    return name[:-2] if name.endswith(":u") else name


lines = open(SRC, encoding="utf-8").read().splitlines()
blocks = []
label = None
i = 0
while i < len(lines):
    if lines[i].startswith("### ") and "cmd:" not in lines[i]:
        label = lines[i][4:].strip()
    if "Performance counter stats" in lines[i]:
        data = {}
        j = i + 1
        while j < len(lines) and "seconds time elapsed" not in lines[j]:
            m = re.match(r"\s*([\d.,]+)\s+(\S+)", lines[j])
            if m:
                try:
                    data[key(m.group(2))] = num(m.group(1))
                except ValueError:
                    pass
            j += 1
        blocks.append((label, data))
        i = j
    i += 1

rows = []
for label, d in blocks:
    cyc = d.get("cycles", 0)
    ins = d.get("instructions", 0)
    br = d.get("branches", 0)
    bm = d.get("branch-misses", 0)
    cr = d.get("cache-references", 0)
    cm = d.get("cache-misses", 0)
    rows.append({
        "cfg": label, "instructions": ins, "cycles": cyc,
        "ipc": ins / cyc if cyc else 0,
        "cs": d.get("context-switches", 0),
        "mig": d.get("cpu-migrations", 0),
        "bmiss": bm / br * 100 if br else 0,
        "cref": cr, "cmiss": cm / cr * 100 if cr else 0,
    })

with open(OUT, "w") as f:
    f.write("| Configuracion | Instrucciones | Cycles | IPC | context-sw | cpu-migr | "
            "Fallo pred. (%) | Cache-ref | Fallo cache (%) |\n")
    f.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['cfg']} | {r['instructions']:.3e} | {r['cycles']:.3e} | "
                f"{r['ipc']:.3f} | {r['cs']:.0f} | {r['mig']:.0f} | "
                f"{r['bmiss']:.4f} | {r['cref']:.0f} | {r['cmiss']:.1f} |\n")

print(open(OUT).read())
