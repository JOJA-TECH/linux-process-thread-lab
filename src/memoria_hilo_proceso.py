"""memoria_hilo_proceso.py - Demuestra comparticion de memoria (hilos) frente a
separacion de espacios de direcciones (procesos) en Linux con Python.

Uso: python3 memoria_hilo_proceso.py

- En la parte de PROCESOS: el hijo (os.fork) modifica la variable global g y
  termina; el padre, tras os.waitpid, observa que su copia NO cambio (espacios
  separados, copy-on-write).
- En la parte de HILOS: un hilo modifica la MISMA variable global y el proceso
  principal SI ve el cambio (memoria compartida).

Equivalente a la version C memoria_hilo_proceso.c.
"""
import os
import sys
import threading

g = 0


def set_g():
    global g
    g = 100  # hilo: escribe en el espacio COMUN
    print("  [hilo]  g = %d (tras escribir 100)" % g)


def main():
    global g

    print("=== PROCESOS (os.fork) ===")
    g = 0
    print("  [padre] antes del fork: g = %d" % g)
    sys.stdout.flush()  # vaciar buffers antes del fork para no duplicarlos
    pid = os.fork()
    if pid == 0:
        g = 100  # hijo: escribe en su COPIA
        print("  [hijo]  g = %d (tras escribir 100), pid=%d" % (g, os.getpid()))
        sys.stdout.flush()  # _exit() no vacia los buffers de stdio
        os._exit(0)
    os.waitpid(pid, 0)
    print("  [padre] despues del wait: g = %d  -> %s"
          % (g, "SEPARADA (cada proceso su memoria)" if g == 0 else "COMPARTIDA"))

    print("=== HILOS (threading) ===")
    g = 0
    print("  [main]  antes del hilo: g = %d" % g)
    t = threading.Thread(target=set_g)
    t.start()
    t.join()
    print("  [main]  despues del join: g = %d  -> %s"
          % (g, "COMPARTIDA (misma memoria)" if g == 100 else "SEPARADA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
