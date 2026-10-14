/*
 * work.h - Carga de trabajo CPU-bound determinista y utilidades de medicion.
 *
 * La misma carga se compila en la version secuencial, la de hilos POSIX y la
 * de procesos. Esto garantiza que todas las configuraciones hagan EXACTAMENTE
 * el mismo tipo de operaciones y permite repartir un numero total de
 * iteraciones (WORK_TOTAL) entre hilos/procesos.
 *
 * La carga es un generador xorshift64 con una dependencia de datos
 * (loop-carried dependency) que impide que el compilador la vectorice o la
 * elimine. El resultado final se publica en un sumidero `volatile` para
 * impedir la optimizacion "dead code elimination".
 */
#ifndef WORK_H
#define WORK_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/times.h>
#include <unistd.h>

/* Constante de mezcla (fraccion de la razon aurea, de splitmix64). */
#define WORK_MIX 0x9E3779B97F4A7C15ULL

/* Sumidero global: obliga a materializar el resultado. NO usar para medir
 * precision: solo impide que el compilador borre el trabajo. */
extern volatile uint64_t g_sink;

/*
 * spin_work: realiza `iters` iteraciones de aritmetica entera con dependencia
 * secuencial. Devuelve un checksum determinista que solo depende de
 * (iters, seed), por lo que sirve para VALIDAR que cada configuracion hizo la
 * misma cantidad de trabajo.
 */
static inline uint64_t spin_work(uint64_t iters, uint64_t seed) {
    uint64_t x = seed | 1ULL; /* nunca 0: un xorshift con estado 0 queda atrapado */
    for (uint64_t i = 0; i < iters; i++) {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        x += i * WORK_MIX;
    }
    return x;
}

/* Tiempo de pared (monotonico) de alta resolucion, en segundos. */
static inline double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/* Tiempo de CPU del PROCESO completo (suma de todos sus hilos), en segundos.
 * En Linux CLOCK_PROCESS_CPUTIME_ID agrega todos los hilos del proceso. */
static inline double proc_cpu_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/* Reparte `total` iteraciones en `n` partes lo mas iguales posible.
 * Escribe en *chunk la parte base y en *remainder cuantas partes reciben
 * una iteracion extra. Asi la suma de las partes == total. */
static inline void split_work(uint64_t total, int n,
                              uint64_t *chunk, uint64_t *remainder) {
    *chunk = total / (uint64_t)n;
    *remainder = total % (uint64_t)n;
}

/* iters asignadas a la unidad `idx` (0-based) de `n` unidades. */
static inline uint64_t work_for(uint64_t total, int n, int idx) {
    uint64_t chunk, rem;
    split_work(total, n, &chunk, &rem);
    return chunk + (idx < (int)rem ? 1ULL : 0ULL);
}

/* Lectura de argumento entero no negativo con validacion. */
static inline uint64_t arg_u64(const char *s) {
    char *end = NULL;
    unsigned long long v = strtoull(s, &end, 10);
    if (end == s || *end != '\0') {
        fprintf(stderr, "argumento no valido: '%s'\n", s);
        exit(EXIT_FAILURE);
    }
    return (uint64_t)v;
}

/* Impresion uniforme y parseable por scripts. */
static inline void report(const char *mode, uint64_t total, int units,
                          double wall, double cpu, uint64_t checksum) {
    int cpus = (int)sysconf(_SC_NPROCESSORS_ONLN);
    double util = (wall > 0.0) ? (cpu / wall) * 100.0 : 0.0;
    printf("RESULT mode=%s units=%d logical_cpus=%d total_iters=%llu "
           "wall_s=%.6f cpu_s=%.6f util_pct=%.2f checksum=%llu\n",
           mode, units, cpus, (unsigned long long)total,
           wall, cpu, util, (unsigned long long)checksum);
}

#endif /* WORK_H */
