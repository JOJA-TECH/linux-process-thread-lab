# Laboratorio: Procesos e Hilos — Versión Python (CPython)

Estudio experimental de **concurrencia, paralelismo, GIL y planificación de CPU en Linux**,
con la misma carga CPU-bound determinista que la versión C (checksums **idénticos**) pero
implementada en **Python**. Se comparan versiones **secuencial**, **con hilos** (`threading`)
y **con procesos** (`os.fork`), midiendo tiempo de pared, tiempo de CPU, utilización,
speedup y eficiencia.

> Esta es la variante Python del laboratorio, en la rama `python` del repositorio.
> La versión C vive en la rama `main`.

## Contenido

```
.
├── Makefile                                   # comprobación de sintaxis (py_compile)
├── src/
│   ├── work.py                                # carga común (bit-exacta con C), temporización, reparto
│   ├── secuencial.py                          # versión secuencial (1 unidad)
│   ├── hilos_threading.py                     # hilos de Python (threading.Thread / join)
│   ├── procesos_fork.py                       # procesos Linux (os.fork / os.waitpid / os.pipe)
│   ├── migracion.py                           # migración de hilos (sched_getcpu + sched_yield)
│   └── memoria_hilo_proceso.py                # memoria compartida vs separada
├── scripts/
│   ├── run_experiments.sh                     # batería de experimentos -> CSV
│   ├── observar_scheduler.sh                  # evidencia de scheduler/GIL (Exp. 5)
│   ├── baseline_carga.py                      # cuantifica la carga de fondo
│   ├── stats.py                               # promedio, desv., speedup, eficiencia
│   ├── perf_mediciones.sh                     # contadores de hardware con perf
│   ├── perf_resumen.py                        # IPC y tasas a partir de perf
│   └── plots.py                               # genera figuras SVG/PNG
├── figuras/                                   # tiempo_vs_hilos, cpu_vs_hilos, speedup_vs_hilos
├── resultados/                                # CSV, logs y estadísticas
└── informe_python_procesos_hilos.md           # informe completo (21 secciones)
```

## Requisitos

- Linux (probado en CachyOS, kernel 7.2.9, x86_64).
- **CPython 3.14** (solo biblioteca estándar; no se requiere NumPy ni matplotlib).
- Para convertir las figuras SVG a PNG: ImageMagick (`magick`/`convert`).
- Herramientas de observación usadas: `taskset`, `ps`, `pidstat`, `lscpu`, `perf`.

## Uso

> Ejecutar **desde la raíz del proyecto** (las rutas son relativas).

```bash
# Carga secuencial: <iteraciones>
python3 src/secuencial.py 3000000

# Hilos (threading, limitados por el GIL): <iteraciones> <n_hilos>
python3 src/hilos_threading.py 3000000 4

# Procesos (fork, paralelismo real): <iteraciones> <n_procesos>
python3 src/procesos_fork.py 3000000 4

# Afinidad de CPU
taskset -c 0        python3 src/procesos_fork.py 3000000 4   # 1 solo procesador lógico
taskset -c 0,2,4,6  python3 src/procesos_fork.py 3000000 4   # 4 núcleos físicos

# Evidencia de migración de hilos: <iters_por_lote> <lotes> <n_hilos>
python3 src/migracion.py 2000 300 24

# Memoria compartida (hilos) vs separada (procesos)
python3 src/memoria_hilo_proceso.py
```

Salida uniforme y parseable (idéntico formato que la versión C):

```
RESULT mode=hilos_threading units=4 logical_cpus=12 total_iters=3000000 \
       wall_s=3.517462 cpu_s=3.473984 util_pct=98.76 checksum=6753946891414406104
```

## Reproducir el informe completo

```bash
make check                              # comprobación de sintaxis (opcional)
./scripts/run_experiments.sh all        # mediciones -> resultados/mediciones.csv
./scripts/observar_scheduler.sh         # evidencia de planificación/GIL
python3 scripts/stats.py                # -> resultados/estadisticas.{csv,md}
python3 scripts/plots.py                # -> figuras/*.svg
./scripts/perf_mediciones.sh            # contadores de hardware -> resultados/perf_mediciones.txt
python3 scripts/perf_resumen.py resultados/perf_mediciones.txt resultados/perf_resumen.md
sudo env OUT=resultados/perf_sudo.txt ./scripts/perf_mediciones.sh  # eventos de kernel (opcional)
```

## Metodología

- Carga **determinista** `xorshift64` con dependencia de datos y sumidero global. Cada
  operación se enmascara a 64 bits (`MASK`) para reproducir el desbordamiento de `uint64_t`
  de C: los checksums son **bit a bit idénticos** a la versión C.
- **Trabajo total constante** repartido entre las unidades (`work_for`): la suma de
  iteraciones es siempre la misma, así que los tiempos son comparables.
- **3 repeticiones** por configuración. El checksum idéntico entre hilos y procesos con el
  mismo número de unidades valida que el trabajo es equivalente.
- Temporización con `time.perf_counter()` (pared) y `time.process_time()` (CPU del
  proceso); en la versión de procesos, `os.times()` (children_user + children_system).
- **Trabajo total = 3 000 000** iteraciones (Python es ~400× más lento por iteración que C).

## Resultados destacados (equipo: AMD Ryzen 5 5500U, 6 núcleos, SMT×2, 12 LP)

| Unidades | Hilos (s) | Speedup | Procesos (s) | Speedup |
|---|---|---|---|---|
| 1 | 3.222 | 1.01 | 3.209 | 1.01 |
| 2 | 3.497 | 0.93 | 1.661 | 1.96 |
| 4 | 3.535 | 0.92 | 0.893 | 3.64 |
| 8 | 3.306 | 0.99 | 0.649 | 5.02 |
| 12 | 3.349 | 0.97 | 0.587 | 5.55 |
| 16 | 3.332 | 0.98 | 0.584 | 5.57 |

- **Los hilos no aceleran** (tiempo plano, utilización ~100 %): el **GIL** solo permite un
  hilo ejecutando bytecode Python a la vez ⇒ **concurrencia sin paralelismo**.
- **Los procesos sí aceleran** (hasta speedup 5.57): cada proceso tiene su propio intérprete
  y su propio GIL. A 4 unidades, procesos = 0.893 s frente a hilos = 3.535 s (**~3.96× más
  rápidos**).
- Afinidad a **1 procesador lógico** con 4 procesos = 3.275 s ⇒ **concurrencia sin
  paralelismo**; con `taskset -c 0,2,4,6`, 0.928 s (paralelismo real).
- **Migración** observable: sin afinidad cada hilo visitó hasta 7 CPUs (hasta 101
  migraciones); con `taskset -c 0`, 0 migraciones (la migración ocurre **aunque el GIL
  impida el paralelismo**).
- **Validación C↔Python**: con igual trabajo total, los checksums coinciden exactamente
  (p. ej. `14414186446203882457` para 1 unidad).
- **`perf`**: instrucciones idénticas (~1.79×10¹⁰) en todas las configuraciones (mismo
  trabajo); IPC ~2.6–2.8.
- Speedup de procesos saturado ~8 por los **6 núcleos físicos** y ~2.6 LP ocupados por el
  escritorio.

## Limitaciones

- Mediciones tomadas en un **escritorio con carga de fondo** (≈21 % de CPU, ~2.6 LP).
- Frecuencia dinámica (governor `powersave` + boost).
- Trabajo total pequeño (3 M) por la lentitud del intérprete; el coste de creación de
  hilos/procesos pesa relativamente más.
- Los eventos de kernel de `perf` (`context-switches`, migraciones) requieren `sudo`.

## Licencia

Uso académico.
