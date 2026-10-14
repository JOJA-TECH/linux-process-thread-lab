/*
 * memoria_hilo_proceso.c - Demuestra comparticion de memoria (hilos) frente a
 * separacion de espacios de direcciones (procesos) en Linux.
 *
 * Uso: ./memoria_hilo_proceso
 *
 * - En la parte de PROCESOS: el hijo modifica la variable global g y termina;
 *   el padre, tras waitpid, observa que SU copia NO cambio (espacios separados,
 *   copy-on-write).
 * - En la parte de HILOS: un hilo modifica la MISMA variable global y el
 *   proceso principal SI ve el cambio (memoria compartida).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <pthread.h>

volatile int g = 0;

static void *set_g(void *arg) {
    (void)arg;
    g = 100;                 /* hilo: escribe en el espacio COMUN */
    printf("  [hilo]  g = %d (tras escribir 100)\n", g);
    return NULL;
}

int main(void) {
    printf("=== PROCESOS (fork) ===\n");
    g = 0;
    printf("  [padre] antes del fork: g = %d\n", g);
    fflush(stdout);          /* vaciar buffers antes del fork para no duplicarlos */
    pid_t pid = fork();
    if (pid == 0) {
        g = 100;             /* hijo: escribe en su COPIA */
        printf("  [hijo]  g = %d (tras escribir 100), pid=%d\n", g, (int)getpid());
        fflush(stdout);      /* _exit() no vacia los buffers de stdio */
        _exit(0);
    }
    int st; waitpid(pid, &st, 0);
    printf("  [padre] despues del wait: g = %d  -> %s\n",
           g, (g == 0) ? "SEPARADA (cada proceso su memoria)" : "COMPARTIDA");

    printf("=== HILOS (pthread) ===\n");
    g = 0;
    printf("  [main]  antes del hilo: g = %d\n", g);
    pthread_t t;
    pthread_create(&t, NULL, set_g, NULL);
    pthread_join(t, NULL);
    printf("  [main]  despues del join: g = %d  -> %s\n",
           g, (g == 100) ? "COMPARTIDA (misma memoria)" : "SEPARADA");
    return 0;
}
