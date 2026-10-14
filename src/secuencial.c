/*
 * secuencial.c - Version secuencial (1 hilo, 1 proceso) de la carga CPU-bound.
 *
 * Uso: ./secuencial [iteraciones] [repeticion]
 *   iteraciones : total de iteraciones de trabajo (por defecto 400000000)
 *   repeticion  : solo una etiqueta para los registros (no afecta el trabajo)
 *
 * Mide tiempo de pared (CLOCK_MONOTONIC) y tiempo de CPU del proceso.
 */
#include "work.h"

volatile uint64_t g_sink = 0;

int main(int argc, char **argv) {
    uint64_t iters = (argc > 1) ? arg_u64(argv[1]) : 400000000ULL;
    int rep = (argc > 2) ? (int)arg_u64(argv[2]) : 1;
    (void)rep;

    double t0_wall = now_sec();
    double t0_cpu  = proc_cpu_sec();

    uint64_t checksum = spin_work(iters, 0x123456789ABCDEFULL);

    double wall = now_sec() - t0_wall;
    double cpu  = proc_cpu_sec() - t0_cpu;

    g_sink ^= checksum; /* impedir dead-code elimination */
    report("secuencial", iters, 1, wall, cpu, checksum);
    return 0;
}
