"""Experimento C3 - cobertura mínima de [0, L] con tramos de sensado (voraz).

Hipótesis
  H3.1  El voraz es óptimo: en el 100 % de las instancias pequeñas su tamaño coincide con
        el óptimo por fuerza bruta (y detecta exactamente las infactibles).
  H3.2  La regla alternativa "el tramo más largo primero" NO es óptima: existen instancias
        donde usa más tramos.
  H3.3  Tiempo total Theta(n log n) (dominado por el ordenamiento): pendiente ~1.0-1.2 y
        T(n)/(n log2 n) ~ constante.
  H3.4  El barrido sobre tramos ya ordenados es Theta(n): pendiente ~1 y examina <= n tramos.
  H3.5  Conteo independiente de la máquina: las comparaciones del merge sort son ~ n log2 n.

Ejecutar:  python -m experimentos.exp_c3  [--rapido]
"""
import json
import math
import os
import sys

import matplotlib.pyplot as plt

from c3_cobertura_intervalos.cobertura import (SinCobertura, barrido_voraz, cobertura_minima,
                                               optimo_fuerza_bruta, voraz_mas_largo)
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import (guardar_csv, medir, pendiente_loglog, pendiente_teorica_nlogn,
                             pendientes_por_rango, razon_nlogn)
from comun.ordenamiento import merge_sort
from datos.generador import tramos_pequenos, tramos_sensado


class _ClaveContada:
    """Envuelve una clave y cuenta cuántas veces el merge sort la compara con '<'."""
    comparaciones = 0
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __lt__(self, otra):
        _ClaveContada.comparaciones += 1
        return self.v < otra.v


def main(rapido=False):
    resumen = {}
    reps = 3 if rapido else 5
    k_max = 16 if rapido else 19

    # ---------------- H3.1 y H3.2 optimalidad
    instancias = 300 if rapido else 2000
    iguales = factibles = infactibles_ok = largo_peor = 0
    exceso_max = 0
    ejemplo = None
    for s in range(instancias):
        n = 4 + s % 8                       # n entre 4 y 11
        tramos, largo = tramos_pequenos(n, semilla=1000 + s)
        opt = optimo_fuerza_bruta(tramos, largo)
        if opt is None:
            try:
                cobertura_minima(tramos, largo)
            except SinCobertura:
                infactibles_ok += 1
            continue
        factibles += 1
        g = len(cobertura_minima(tramos, largo))
        iguales += g == opt
        h = voraz_mas_largo(tramos, largo)
        if h is not None and len(h) > opt:
            largo_peor += 1
            if len(h) - opt > exceso_max:
                exceso_max = len(h) - opt
                ejemplo = {"tramos": tramos, "largo": largo, "optimo": opt, "mas_largo": len(h)}
    resumen["optimalidad"] = {
        "instancias": instancias, "factibles": factibles,
        "voraz_igual_al_optimo": iguales,
        "infactibles_detectadas": infactibles_ok, "infactibles": instancias - factibles,
        "mas_largo_primero_suboptimo": largo_peor, "exceso_maximo_mas_largo": exceso_max,
        "ejemplo_suboptimo": ejemplo,
    }

    # ---------------- H3.3 tiempo total y H3.4 barrido
    tam = [2 ** k for k in range(10, k_max + 1)]
    gen = lambda n: tramos_sensado(n)
    total = medir(lambda d: cobertura_minima(d[0], d[1]), gen, tam, reps)
    ordenar = medir(lambda d: merge_sort(d[0], key=lambda t: t[0]), gen, tam, reps)
    gen_ord = lambda n: (lambda tr, L: (merge_sort(tr, key=lambda t: t[0]), L))(*tramos_sensado(n))
    barrido = medir(lambda d: barrido_voraz(d[0], d[1]), gen_ord, tam, reps)
    for f in total:
        tr, L = tramos_sensado(f["n"])
        c = {}
        f["elegidos"] = len(cobertura_minima(tr, L, c))
        f["examinados"] = c["examinados"]
        _ClaveContada.comparaciones = 0
        merge_sort(tr, key=lambda t: _ClaveContada(t[0]))
        f["comparaciones_orden"] = _ClaveContada.comparaciones
        f["comparaciones_sobre_nlogn"] = f["comparaciones_orden"] / (f["n"] * math.log2(f["n"]))
    guardar_csv(os.path.join(CARPETA, "c3_tiempo.csv"), total,
                ["n", "mediana", "q1", "q3", "minimo", "elegidos", "examinados",
                 "comparaciones_orden", "comparaciones_sobre_nlogn"])
    guardar_csv(os.path.join(CARPETA, "c3_barrido.csv"), barrido, ["n", "mediana", "q1", "q3"])
    resumen["pendientes"] = loglog(
        [("voraz completo", total), ("solo ordenamiento", ordenar), ("solo barrido", barrido)],
        "C3: cobertura mínima, tiempo vs n (log-log)", "c3_loglog.png")
    resumen["pendientes_por_rango"] = {"voraz completo": pendientes_por_rango(total),
                                       "solo barrido": pendientes_por_rango(barrido)}
    resumen["pendiente_teorica_nlogn"] = pendiente_teorica_nlogn([f["n"] for f in total])
    resumen["comparaciones_sobre_nlogn"] = {str(f["n"]): f["comparaciones_sobre_nlogn"] for f in total}
    resumen["pendiente_comparaciones"] = pendiente_loglog([f["n"] for f in total],
                                                          [f["comparaciones_orden"] for f in total])[0]
    ns = [f["n"] for f in total]
    r = razon_nlogn(ns, [f["mediana"] for f in total])
    resumen["razon_nlogn"] = dict(zip(map(str, ns), r))
    resumen["examinados_igual_n"] = all(f["examinados"] <= f["n"] for f in total)
    resumen["fraccion_tiempo_ordenamiento"] = {
        str(a["n"]): a["mediana"] / b["mediana"] for a, b in zip(ordenar, total)}
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.plot(ns, [x * 1e6 for x in r], "o-", color=COLORES[0], ms=4)
    ax.set_xscale("log", base=2)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("n")
    ax.set_ylabel("T(n) / (n log2 n)  [µs]")
    ax.set_title("C3: la razón T(n)/(n log n) se estabiliza")
    guardar(fig, "c3_razon_nlogn.png")

    with open(os.path.join(CARPETA, "c3_resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in resumen.items() if k != "razon_nlogn"}, indent=2,
                     ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
