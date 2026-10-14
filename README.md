# Laboratorio de Sistemas Operativos: Procesos e Hilos

Estudio experimental de **concurrencia, paralelismo y planificación de CPU en Linux**.
Se implementa una carga CPU-bound determinista en C y se compara el comportamiento de
versiones **secuenciales**, **con hilos POSIX** y **con procesos (`fork`)**, midiendo
tiempo de pared, tiempo de CPU, utilización, speedup y eficiencia.

## Contenido

```
.
├── Makefile                                   # compilación de las variantes Linux
├── src/
│   ├── work.h                                 # carga común, temporización y reparto de trabajo
│   ├── secuencial.c                           # versión secuencial (1 unidad)
│   ├── hilos_pthread.c                        # hilos POSIX (pthread_create / pthread_join)
│   ├── procesos_fork.c                        # procesos Linux (fork / waitpid / pipe)
│   ├── migracion.c                            # demuestra migración de hilos (sched_getcpu)
│   └── memoria_hilo_proceso.c                 # memoria compartida vs separada
├── scripts/
│   ├── run_experiments.sh                     # batería de experimentos -> CSV
│   ├── observar_scheduler.sh                  # evidencia de scheduler/CPU (Exp. 5)
│   ├── baseline_carga.py                      # cuantifica la carga de fondo
│   ├── stats.py                               # promedio, desv., speedup, eficiencia
│   ├── perf_mediciones.sh                     # contadores de hardware con perf
│   ├── perf_resumen.py                        # IPC y tasas a partir de perf
│   └── plots.py                               # genera figuras SVG/PNG
├── figuras/                                   # tiempo_vs_hilos, cpu_vs_hilos, speedup_vs_hilos
├── resultados/                                # CSV, logs y estadísticas
└── bin/                                       # ejecutables (generados por make)
```

## Requisitos

- Linux (probado en CachyOS, kernel 7.2.9, x86_64).
- `gcc` con soporte de C11 y `pthreads`.
- Para las gráficas: `python3` (módulo `numpy` opcional) e ImageMagick (`magick`/`convert`).
- Herramientas de observación usadas: `taskset`, `ps`, `top`, `pidstat`, `mpstat`, `lscpu`, `perf`.

## Compilación

```bash
make            # gcc -O2 -std=c11 -Wall -Wextra -pthread
make clean
```

## Uso

```bash
# Carga secuencial: <iteraciones>
./bin/secuencial 800000000

# Hilos: <iteraciones> <n_hilos>
./bin/hilos_pthread 800000000 4

# Procesos: <iteraciones> <n_procesos>
./bin/procesos_fork 800000000 4

# Afinidad de CPU
taskset -c 0        ./bin/hilos_pthread 800000000 4   # 1 solo procesador lógico
taskset -c 0,2,4,6  ./bin/hilos_pthread 800000000 4   # 4 núcleos físicos

# Evidencia de migración de hilos: <iters_por_lote> <lotes> <n_hilos>
./bin/migracion 1000000 300 24

# Memoria compartida (hilos) vs separada (procesos)
./bin/memoria_hilo_proceso
```

Salida uniforme y parseable:

```
RESULT mode=hilos_pthread units=4 logical_cpus=12 total_iters=800000000 \
       wall_s=0.751255 cpu_s=2.855047 util_pct=380.04 checksum=4314293330488784900
```

## Reproducir el informe completo

```bash
make
./scripts/run_experiments.sh all        # mediciones -> resultados/mediciones.csv
./scripts/observar_scheduler.sh         # evidencia de planificación/CPU
python3 scripts/stats.py                # -> resultados/estadisticas.{csv,md}
python3 scripts/plots.py                # -> figuras/*.svg
./scripts/perf_mediciones.sh            # contadores de hardware -> resultados/perf_mediciones.txt
python3 scripts/perf_resumen.py         # -> resultados/perf_resumen.md
sudo env OUT=resultados/perf_sudo.txt ./scripts/perf_mediciones.sh   # eventos de kernel (context-switches, migraciones)
```

## Metodología

- Carga **determinista** `xorshift64` con dependencia de datos y sumidero `volatile`
  (evita que el compilador la elimine). No es un benchmark científico.
- **Trabajo total constante** repartido entre las unidades (`work_for`): la suma de
  iteraciones es siempre la misma, así que los tiempos son comparables.
- Cada configuración se ejecuta **3 veces**. El checksum idéntico entre hilos y procesos
  con el mismo número de unidades valida que el trabajo es equivalente.
- Temporización con `CLOCK_MONOTONIC` (pared) y `CLOCK_PROCESS_CPUTIME_ID` (CPU del
  proceso); en la versión de procesos, `getrusage(RUSAGE_CHILDREN)`.

## Resultados destacados (equipo: AMD Ryzen 5 5500U, 6 núcleos, SMT×2, 12 LP)

| Unidades | Hilos (s) | Speedup | Procesos (s) | Speedup |
|---|---|---|---|---|
| 1 | 2.742 | 1.00 | 2.748 | 1.00 |
| 2 | 1.372 | 2.00 | 1.380 | 1.99 |
| 4 | 0.729 | 3.75 | 0.695 | 3.94 |
| 8 | 0.380 | 7.21 | 0.380 | 7.20 |
| 12 | 0.373 | 7.34 | 0.367 | 7.47 |
| 16 | 0.345 | 7.93 | 0.323 | 8.48 |

- Afinidad a **1 procesador lógico** con 4 hilos = 2.762 s ⇒ **concurrencia sin paralelismo**.
- **Migración** observable: hilos visitan hasta 5 CPUs distintas; con `taskset -c 0`, 0 migraciones.
- **`perf`**: instrucciones idénticas (~1.04×10¹⁰) en todas las configuraciones; el **IPC cae de ~1.85 (1 hilo) a ~1.70 (8–16 hilos)** por contención SMT; los **cambios de contexto** saltan de ~20–50 (hilos ≤ núcleos) a 1253 (12 hilos) y 2108 (4 hilos en 1 LP).
- Speedup saturado ~8 por los **6 núcleos físicos** y ~2 LP ocupados por el escritorio.

## Limitaciones

- Mediciones tomadas en un **escritorio con carga de fondo** (≈17 % de CPU, ~2 LP).
- Frecuencia dinámica (governor `powersave` + boost).
- `perf` con eventos de usuario y de kernel (`sudo`); falta `turbostat` (frecuencia real por núcleo).

## Licencia

Uso académico.
