"""Ejecuta todos los experimentos (C1 a C6).

    python -m experimentos.ejecutar_todos            # tamaños completos (~15 min)
    python -m experimentos.ejecutar_todos --rapido   # versión corta para revisar (~1 min)

Los CSV, JSON y PNG quedan en resultados/.
"""
import sys
import time

from experimentos import exp_c1, exp_c2, exp_c3, exp_c4, exp_c5, exp_c6

if __name__ == "__main__":
    rapido = "--rapido" in sys.argv
    for nombre, mod in [("C1", exp_c1), ("C2", exp_c2), ("C3", exp_c3), ("C4", exp_c4),
                      ("C5", exp_c5), ("C6", exp_c6)]:
        t0 = time.perf_counter()
        print(f"\n===== {nombre} =====")
        mod.main(rapido)
        print(f"[{nombre} terminado en {time.perf_counter() - t0:.1f} s]")
