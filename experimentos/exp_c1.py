"""Experimento C1 - par de puntos más cercanos.

Hipótesis
  H1.1  D&V es Theta(n log n): pendiente log-log en [1.0, 1.2] y T(n)/(n log2 n) ~ constante,
        para las tres distribuciones (uniforme, agrupada, vertical).
  H1.2  Fuerza bruta es Theta(n²): pendiente log-log ~ 2.
  H1.3  En la franja cada punto se compara con a lo sumo 7 vecinos.
  H1.4  Conteo independiente de la máquina: el trabajo de combinación (mezcla + franja) de D&V
        es ~ 2 n log2 n; las distancias calculadas por D&V son O(n log n) (con datos uniformes
        se espera Theta(n), porque la franja es pequeña) y las de fuerza bruta son n(n-1)/2.

Ejecutar:  python -m experimentos.exp_c1  [--rapido]
"""
import json
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

from c1_par_mas_cercano.par_cercano import Contador, fuerza_bruta, par_mas_cercano
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import (guardar_csv, medir, pendiente_loglog, pendiente_teorica_nlogn,
                             pendientes_por_rango, razon_nlogn)
from datos.generador import nube_puntos_2d


def main(rapido=False):
    k_max = 15 if rapido else 18
    reps = 3 if rapido else 5
    tam_dv = [2 ** k for k in range(6, k_max + 1)]
    tam_fb = [2 ** k for k in range(6, (11 if rapido else 12) + 1)]
    resumen = {}

    series = []
    for dist in ["uniforme", "agrupada", "vertical"]:
        filas = medir(par_mas_cercano, lambda n, d=dist: nube_puntos_2d(n, d), tam_dv, reps)
        for f in filas:
            c = Contador()
            par_mas_cercano(nube_puntos_2d(f["n"], dist), c)
            f["distancias"] = c.distancias
            f["combinacion"] = c.combinacion
            f["max_franja"] = c.max_por_punto_franja
        guardar_csv(os.path.join(CARPETA, f"c1_dv_{dist}.csv"), filas,
                    ["n", "mediana", "q1", "q3", "minimo", "distancias", "combinacion", "max_franja"])
        series.append((f"D&V {dist}", filas))
    fb = medir(fuerza_bruta, lambda n: nube_puntos_2d(n), tam_fb, reps)
    for f in fb:
        f["distancias"] = f["n"] * (f["n"] - 1) // 2
    guardar_csv(os.path.join(CARPETA, "c1_fuerza_bruta.csv"), fb,
                ["n", "mediana", "q1", "q3", "minimo", "distancias"])
    series.append(("fuerza bruta", fb))

    pend = loglog(series, "C1: par más cercano, tiempo vs n (log-log)", "c1_loglog.png",
                  n_min_ajuste=2 ** 10)
    resumen["pendientes_tiempo"] = pend
    resumen["pendiente_teorica_nlogn_2^10_a_max"] = pendiente_teorica_nlogn(
        [n for n in tam_dv if n >= 2 ** 10])
    resumen["pendientes_por_rango"] = {etq: pendientes_por_rango(filas) for etq, filas in series[:3]}

    # T(n) / (n log2 n)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    resumen["razon_nlogn"] = {}
    for k, (etq, filas) in enumerate(series[:3]):
        ns = [f["n"] for f in filas]
        r = razon_nlogn(ns, [f["mediana"] for f in filas])
        resumen["razon_nlogn"][etq] = dict(zip(map(str, ns), r))
        ax.plot(ns, [x * 1e6 for x in r], "o-", color=COLORES[k], ms=4, label=etq)
    ax.set_xscale("log", base=2)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("n")
    ax.set_ylabel("T(n) / (n log2 n)  [µs]")
    ax.set_title("C1: la razón T(n)/(n log n) se estabiliza")
    ax.legend(fontsize=8)
    guardar(fig, "c1_razon_nlogn.png")

    # Conteos independientes de la máquina
    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    ns = np.array([f["n"] for f in series[0][1]], float)
    cb = np.array([f["combinacion"] for f in series[0][1]], float)
    dv = np.array([f["distancias"] for f in series[0][1]], float)
    dvv = np.array([f["distancias"] for f in series[2][1]], float)
    nsb = np.array([f["n"] for f in fb], float)
    bf = np.array([f["distancias"] for f in fb], float)
    big = ns >= 1024
    ax.loglog(ns, cb, "o-", color=COLORES[0], ms=4,
              label=f"D&V: trabajo de combinación (pend. {pendiente_loglog(ns[big], cb[big])[0]:.2f})")
    ax.loglog(ns, dv, "^-", color=COLORES[2], ms=4,
              label=f"D&V: distancias, uniforme (pend. {pendiente_loglog(ns[big], dv[big])[0]:.2f})")
    ax.loglog(ns, dvv, "v-", color=COLORES[4], ms=4,
              label=f"D&V: distancias, vertical (pend. {pendiente_loglog(ns[big], dvv[big])[0]:.2f})")
    ax.loglog(nsb, bf, "s-", color=COLORES[3], ms=4,
              label=f"fuerza bruta: distancias (pend. {pendiente_loglog(nsb, bf)[0]:.2f})")
    ax.loglog(ns, 2 * ns * np.log2(ns), "--", color="gray", lw=1, label="2 n log2 n")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("n")
    ax.set_ylabel("operaciones contadas")
    ax.set_title("C1: operaciones contadas (no dependen de la máquina)")
    ax.legend(fontsize=7)
    guardar(fig, "c1_operaciones.png")
    resumen["pendientes_operaciones"] = {
        "combinacion": pendiente_loglog(ns[big], cb[big])[0],
        "distancias_uniforme": pendiente_loglog(ns[big], dv[big])[0],
        "distancias_vertical": pendiente_loglog(ns[big], dvv[big])[0],
        "distancias_fuerza_bruta": pendiente_loglog(nsb, bf)[0]}
    resumen["combinacion_sobre_nlogn"] = {
        str(int(n)): float(c / (n * math.log2(n))) for n, c in zip(ns, cb)}
    resumen["distancias_sobre_n"] = {
        etq: {str(f["n"]): f["distancias"] / f["n"] for f in filas} for etq, filas in series[:3]}
    resumen["max_vecinos_franja"] = {etq: max(f["max_franja"] for f in filas)
                                     for etq, filas in series[:3]}

    # Punto de cruce: primer n medido en el que D&V es más rápido que fuerza bruta.
    t_dv = {f["n"]: f["mediana"] for f in series[0][1]}
    cruce = next((f["n"] for f in fb if t_dv.get(f["n"], math.inf) < f["mediana"]), None)
    resumen["cruce_dv_mas_rapido_desde_n"] = cruce
    resumen["speedup_en_n_max_fb"] = fb[-1]["mediana"] / t_dv[fb[-1]["n"]]

    with open(os.path.join(CARPETA, "c1_resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    print(json.dumps(resumen["pendientes_tiempo"], indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
