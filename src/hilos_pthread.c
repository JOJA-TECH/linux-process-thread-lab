/*
 * hilos_pthread.c - Version con hilos POSIX (pthreads) para Linux.
 *
 * Uso: ./hilos_pthread [iteraciones] [n_hilos] [repeticion]
 *   iteraciones : total de iteraciones de trabajo (por defecto 400000000)
 *   n_hilos     : numero de hilos a crear (por defecto 4)
 *
 * El trabajo TOTAL se reparte entre los hilos con work_for(), de modo que la
 * suma de iteraciones de todos los hilos es exactamente el total pedido. Asi
 * todas las configuraciones (1, 2, 4, 8, 16 hilos) hacen la MISMA cantidad de
 * trabajo y sus tiempos son comparables.
 *
 * Cada hilo escribe su checksum en una casilla propia del arreglo `partial`
 * (no hay condicion de carrera ni necesidad de mutex). Solo se sincroniza con
 * pthread_join al final. El checksum total permite validar el trabajo.
 */
#include "work.h"
#include <pthread.h>

volatile uint64_t g_sink = 0;

typedef struct {
    uint64_t iters;   /* iteraciones asignadas a este hilo */
    uint64_t seed;    /* semilla distinta para evitar contenido identico */
    uint64_t result;  /* salida: checksum parcial */
} thread_arg_t;

static void *thread_main(void *p) {
    thread_arg_t *a = (thread_arg_t *)p;
    a->result = spin_work(a->iters, a->seed);
    return NULL;
}

int main(int argc, char **argv) {
    uint64_t total = (argc > 1) ? arg_u64(argv[1]) : 400000000ULL;
    int n = (argc > 2) ? (int)arg_u64(argv[2]) : 4;
    if (n < 1) { fprintf(stderr, "n_hilos debe ser >= 1\n"); return EXIT_FAILURE; }

    pthread_t *tids = calloc((size_t)n, sizeof(pthread_t));
    thread_arg_t *args = calloc((size_t)n, sizeof(thread_arg_t));
    if (!tids || !args) { perror("calloc"); return EXIT_FAILURE; }

    /* Preparar argumentos ANTES de cronometrar (el reparto no es la carga). */
    for (int i = 0; i < n; i++) {
        args[i].iters = work_for(total, n, i);
        args[i].seed  = 0x123456789ABCDEFULL + (uint64_t)i * 0x100000001B3ULL;
        args[i].result = 0;
    }

    double t0_wall = now_sec();
    double t0_cpu  = proc_cpu_sec();

    /* Creacion de los hilos. */
    for (int i = 0; i < n; i++) {
        int rc = pthread_create(&tids[i], NULL, thread_main, &args[i]);
        if (rc != 0) {
            fprintf(stderr, "pthread_create hilo %d fallo: %d\n", i, rc);
            n = i; /* usar solo los hilos creados */
            break;
        }
    }

    /* Espera y liberacion de recursos. */
    uint64_t checksum = 0;
    for (int i = 0; i < n; i++) {
        int rc = pthread_join(tids[i], NULL);
        if (rc != 0) fprintf(stderr, "pthread_join hilo %d fallo: %d\n", i, rc);
        checksum ^= args[i].result;
    }

    double wall = now_sec() - t0_wall;
    double cpu  = proc_cpu_sec() - t0_cpu;

    g_sink ^= checksum;
    report("hilos_pthread", total, n, wall, cpu, checksum);

    free(tids);
    free(args);
    return 0;
}
