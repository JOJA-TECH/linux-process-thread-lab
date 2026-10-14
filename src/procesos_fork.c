/*
 * procesos_fork.c - Version con procesos para Linux (fork/waitpid).
 *
 * Uso: ./procesos_fork [iteraciones] [n_procesos] [repeticion]
 *
 * El proceso padre crea n procesos hijo con fork(). Cada hijo recibe su parte
 * del trabajo TOTAL (work_for), la ejecuta y comunica su checksum al padre por
 * una tuberia (pipe) usando un registro de tamano fijo. Los espacios de
 * direcciones son independientes (cada hijo tiene su propia copia del
 * acumulador); la unica comunicacion es el pipe.
 *
 * El padre espera a cada hijo con waitpid() y acumula el uso de CPU de los
 * hijos mediante getrusage(RUSAGE_CHILDREN), de modo que la utilizacion
 * reportada incluye el tiempo de CPU de los procesos hijo.
 */
#include "work.h"
#include <sys/wait.h>
#include <sys/resource.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

volatile uint64_t g_sink = 0;

typedef struct {
    pid_t pid;
    uint64_t iters;
    uint64_t checksum;
} record_t;

static double children_cpu_sec(void) {
    struct rusage ru;
    if (getrusage(RUSAGE_CHILDREN, &ru) != 0) return 0.0;
    double u = (double)ru.ru_utime.tv_sec + (double)ru.ru_utime.tv_usec / 1e6;
    double s = (double)ru.ru_stime.tv_sec + (double)ru.ru_stime.tv_usec / 1e6;
    return u + s;
}

int main(int argc, char **argv) {
    uint64_t total = (argc > 1) ? arg_u64(argv[1]) : 400000000ULL;
    int n = (argc > 2) ? (int)arg_u64(argv[2]) : 4;
    if (n < 1) { fprintf(stderr, "n_procesos debe ser >= 1\n"); return EXIT_FAILURE; }

    int fd[2];
    if (pipe(fd) != 0) { perror("pipe"); return EXIT_FAILURE; }

    double cpu_before = children_cpu_sec();
    double wall0 = now_sec();

    pid_t *kids = calloc((size_t)n, sizeof(pid_t));
    if (!kids) { perror("calloc"); return EXIT_FAILURE; }

    for (int i = 0; i < n; i++) {
        pid_t pid = fork();
        if (pid < 0) { perror("fork"); n = i; break; }
        if (pid == 0) {
            /* ---- Proceso hijo ---- */
            close(fd[0]); /* el hijo no lee */
            uint64_t iters = work_for(total, n, i);
            uint64_t seed  = 0x123456789ABCDEFULL + (uint64_t)i * 0x100000001B3ULL;
            uint64_t sum   = spin_work(iters, seed);
            record_t rec = { .pid = getpid(), .iters = iters, .checksum = sum };
            ssize_t w = write(fd[1], &rec, sizeof rec);
            if (w != (ssize_t)sizeof rec) _exit(2);
            close(fd[1]);
            _exit(0); /* _exit evita duplicar buffers de stdio */
        }
        kids[i] = pid; /* proceso padre */
    }

    /* El padre cierra el extremo de escritura para que read() vea EOF. */
    close(fd[1]);

    uint64_t checksum = 0;
    record_t rec;
    ssize_t r;
    while ((r = read(fd[0], &rec, sizeof rec)) > 0) {
        if (r == (ssize_t)sizeof rec) {
            checksum ^= rec.checksum;
            fprintf(stderr, "[fork] hijo pid=%d iters=%llu checksum=%llu\n",
                    (int)rec.pid, (unsigned long long)rec.iters,
                    (unsigned long long)rec.checksum);
        }
    }
    close(fd[0]);

    /* Esperar a TODOS los hijos (incluidos los que no escribieron). */
    for (int i = 0; i < n; i++) {
        int status = 0;
        if (waitpid(kids[i], &status, 0) < 0 && errno != ECHILD)
            perror("waitpid");
    }

    double wall = now_sec() - wall0;
    double cpu  = children_cpu_sec() - cpu_before;

    g_sink ^= checksum;
    report("procesos_fork", total, n, wall, cpu, checksum);

    free(kids);
    return 0;
}
