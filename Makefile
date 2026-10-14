# Makefile - Laboratorio de procesos e hilos (Linux)
#
# Todas las variantes se compilan con las MISMAS opciones (-O2, gcc) para que
# las comparaciones sean validas. Proyecto exclusivamente para Linux.

CC      := gcc
CFLAGS  := -O2 -std=c11 -Wall -Wextra -pthread
BINDIR  := bin
SRCDIR  := src

TARGETS := $(BINDIR)/secuencial \
           $(BINDIR)/hilos_pthread \
           $(BINDIR)/procesos_fork \
           $(BINDIR)/migracion \
           $(BINDIR)/memoria_hilo_proceso

.PHONY: all clean
all: $(TARGETS)

$(BINDIR):
	mkdir -p $(BINDIR)

$(BINDIR)/secuencial: $(SRCDIR)/secuencial.c $(SRCDIR)/work.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $(SRCDIR)/secuencial.c

$(BINDIR)/hilos_pthread: $(SRCDIR)/hilos_pthread.c $(SRCDIR)/work.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $(SRCDIR)/hilos_pthread.c

$(BINDIR)/procesos_fork: $(SRCDIR)/procesos_fork.c $(SRCDIR)/work.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $(SRCDIR)/procesos_fork.c

$(BINDIR)/migracion: $(SRCDIR)/migracion.c $(SRCDIR)/work.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $(SRCDIR)/migracion.c

$(BINDIR)/memoria_hilo_proceso: $(SRCDIR)/memoria_hilo_proceso.c | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $(SRCDIR)/memoria_hilo_proceso.c

clean:
	rm -rf $(BINDIR)
