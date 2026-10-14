/*
 * migracion.c - Evidencia de migracion de hilos entre procesadores logicos.
 *
 * Uso: ./migracion [iteraciones_por_lote] [n_lotes] [n_workers]
 *
 * Cada hilo trabajador ejecuta lotes cortos de trabajo CPU-bound, cede la CPU
 * (sched_yield) y, entre lote y lote, consulta con sched_getcpu() en que
 * procesador logico esta corriendo. Registra el conjunto de CPUs observados y
 * cuenta los cambios (migraciones).
 *
 * Si hay MAS hilos que procesadores logicos (n_workers > nproc), el balanceador
 * de carga del scheduler se ve forzado a mover hilos entre CPUs y las
 * migraciones se hacen visibles. Con afinidad fija (taskset -c 0) todos los
 * hilos quedan en una sola CPU y no hay migracion posible.
 */
#define _GNU_SOURCE
#include "work.h"
#include <pthread.h>
#include <sched.h>

volatile uint64_t g_sink = 0;

typedef struct { uint64_t iters; int lotes; int id; } targ_t;

static void *worker(void *p) {
    targ_t *a = (targ_t *)p;
    int seen[64]; for (int i = 0; i < 64; i++) seen[i] = 0;
    int last = -1, migrations = 0, distinct = 0;
    for (int l = 0; l < a->lotes; l++) {
        g_sink ^= spin_work(a->iters, 0xABCDEFULL + (uint64_t)l);
        int cpu = sched_getcpu();
        if (cpu >= 0 && cpu < 64) {
            if (!seen[cpu]) { seen[cpu] = 1; distinct++; }
            if (last != -1 && cpu != last) migrations++;
            last = cpu;
        }
        sched_yield(); /* da oportunidad al scheduler de balancear/migrar */
    }
    printf("  worker %2d: distinct_cpus=%d migrations=%d lista=", a->id, distinct, migrations);
    for (int i = 0; i < 64; i++) if (seen[i]) printf("%d ", i);
    printf("\n");
    return NULL;
}

int main(int argc, char **argv) {
    uint64_t iters_lote = (argc > 1) ? arg_u64(argv[1]) : 1000000ULL;
    int lotes    = (argc > 2) ? (int)arg_u64(argv[2]) : 300;
    int nworkers = (argc > 3) ? (int)arg_u64(argv[3]) : 24;

    printf("INICIO pid=%d cpu_actual=%d logical_cpus=%ld n_workers=%d\n",
           (int)getpid(), sched_getcpu(), sysconf(_SC_NPROCESSORS_ONLN), nworkers);

    pthread_t *t = calloc((size_t)nworkers, sizeof(pthread_t));
    targ_t *a = calloc((size_t)nworkers, sizeof(targ_t));
    if (!t || !a) { perror("calloc"); return 1; }
    for (int i = 0; i < nworkers; i++) {
        a[i].iters = iters_lote; a[i].lotes = lotes; a[i].id = i;
        if (pthread_create(&t[i], NULL, worker, &a[i]) != 0) { perror("pthread_create"); return 1; }
    }
    for (int i = 0; i < nworkers; i++) pthread_join(t[i], NULL);
    free(t); free(a);
    return 0;
}
