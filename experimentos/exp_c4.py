"""Experimento C4 - backtracking en cuadrícula de ocupación (maniobra de parqueo / evasión).

Hipótesis
  H4.1  Sin poda, los nodos del árbol de búsqueda crecen exponencialmente con el número de celdas
        (recta en escala semilogarítmica); con k = 7 ya se acercan a 10^6.
  H4.2  La poda con cota de Manhattan da la MISMA longitud mínima y explora órdenes de magnitud
        menos nodos (razón sin poda / con poda creciente con el tamaño).
  H4.3  BFS es Theta(V): pendiente log-log del tiempo ~1 entre 2^10 y 2^20 celdas.
  H4.4  La poda no cambia el peor caso exponencial: en cuadrículas grandes con obstáculos los
        nodos con poda crecen mucho más rápido que V (frente a BFS, que crece como V).

Ejecutar:  python -m experimentos.exp_c4  [--rapido]
"""
import json
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

from c4_backtracking_cuadricula.backtracking import (LimiteExcedido, backtracking_con_poda,
                                                     backtracking_sin_poda, bfs)
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import guardar_csv, medir, pendiente_loglog
from comun.ordenamiento import merge_sort
from datos.generador import cuadricula_ocupacion, estacionamiento

DENSIDAD = 0.2
LIMITE = 3_000_000


def _nodos(funcion, grid, a, b):
    try:
        d, _, est = funcion(grid, a, b, limite_nodos=LIMITE)
        return est.nodos, d
    except LimiteExcedido:
        return None, None


def main(rapido=False):
    resumen = {}
    instancias = 5 if rapido else 10
    reps = 3 if rapido else 5

    # ---------------- E1: los tres algoritmos en cuadrículas pequeñas (k x k)
    ks = [3, 4, 5, 6] if rapido else [3, 4, 5, 6, 7]
    filas = []
    for k in ks:
        sin, con, anch, cortes = [], [], [], 0
        casos = []
        for s in range(instancias):
            grid, a, b = cuadricula_ocupacion(k, k, DENSIDAD, semilla=1000 * k + s)
            n_sin, d_sin = _nodos(backtracking_sin_poda, grid, a, b)
            n_con, d_con = _nodos(backtracking_con_poda, grid, a, b)
            d_bfs, _, e_bfs = bfs(grid, a, b)
            assert d_con == d_bfs and (d_sin is None or d_sin == d_bfs)
            if n_sin is None:
                cortes += 1
                n_sin = LIMITE
            sin.append(n_sin)
            con.append(n_con)
            anch.append(e_bfs.nodos)
            casos.append((n_sin, grid, a, b))
        # Tiempo (5 repeticiones) sobre la instancia de mediana de nodos sin poda.
        casos_ordenados = merge_sort(casos, key=lambda c: c[0])
        _, grid, a, b = casos_ordenados[len(casos) // 2]
        t_sin = medir(lambda g: backtracking_sin_poda(*g, limite_nodos=LIMITE), lambda _: (grid, a, b), [k], reps)[0]
        t_con = medir(lambda g: backtracking_con_poda(*g), lambda _: (grid, a, b), [k], reps)[0]
        t_bfs = medir(lambda g: bfs(*g), lambda _: (grid, a, b), [k], reps)[0]
        filas.append({
            "k": k, "celdas": k * k,
            "nodos_sin_poda_mediana": float(np.median(sin)), "nodos_sin_poda_q1": float(np.percentile(sin, 25)),
            "nodos_sin_poda_q3": float(np.percentile(sin, 75)), "nodos_sin_poda_max": int(max(sin)),
            "instancias_cortadas": cortes,
            "nodos_con_poda_mediana": float(np.median(con)), "nodos_con_poda_max": int(max(con)),
            "nodos_bfs_mediana": float(np.median(anch)),
            "razon_sin_con": float(np.median([x / y for x, y in zip(sin, con)])),
            "t_sin_poda_s": t_sin["mediana"], "t_con_poda_s": t_con["mediana"], "t_bfs_s": t_bfs["mediana"],
        })
    guardar_csv(os.path.join(CARPETA, "c4_pequenas.csv"), filas, list(filas[0].keys()))
    V = np.array([f["celdas"] for f in filas], float)
    sinp = np.array([f["nodos_sin_poda_mediana"] for f in filas])
    pend_exp, _ = np.polyfit(V, np.log(sinp), 1)        # log(nodos) = a·V + c
    resumen["pequenas"] = filas
    resumen["factor_crecimiento_por_celda_sin_poda"] = float(math.exp(pend_exp))

    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    ax.errorbar(V, sinp, yerr=[sinp - [f["nodos_sin_poda_q1"] for f in filas],
                               np.array([f["nodos_sin_poda_q3"] for f in filas]) - sinp],
                fmt="o-", color=COLORES[1], ms=4, capsize=2, label="backtracking sin poda")
    ax.plot(V, [f["nodos_con_poda_mediana"] for f in filas], "s-", color=COLORES[0], ms=4,
            label="backtracking con poda (Manhattan)")
    ax.plot(V, [f["nodos_bfs_mediana"] for f in filas], "^-", color=COLORES[2], ms=4, label="BFS")
    ax.set_yscale("log")
    ax.set_xlabel("celdas de la cuadrícula (k x k)")
    ax.set_ylabel("nodos explorados (mediana)")
    ax.set_title(f"C4: sin poda crece ~{math.exp(pend_exp):.2f}x por celda (escala semilog)")
    ax.legend(fontsize=8)
    guardar(fig, "c4_nodos_pequenas.png")

    # ---------------- E2: escala (BFS hasta 2^20 celdas; poda mientras no explote)
    lados = [32, 64, 128, 256, 512] if rapido else [32, 45, 64, 90, 128, 181, 256, 362, 512, 724, 1024]
    t_bfs = medir(lambda g: bfs(*g), lambda k: cuadricula_ocupacion(k, k, DENSIDAD, semilla=k),
                  lados, reps)
    for f, k in zip(t_bfs, lados):
        f["k"] = k
        f["n"] = k * k
    guardar_csv(os.path.join(CARPETA, "c4_bfs.csv"), t_bfs, ["k", "n", "mediana", "q1", "q3", "minimo"])
    resumen["pendiente_bfs"] = loglog([("BFS", t_bfs)], "C4: BFS, tiempo vs celdas (log-log)",
                                      "c4_bfs_loglog.png", xlabel="celdas V = k²")["BFS"]

    lados_p = [8, 11, 16, 23, 32] if not rapido else [8, 11, 16]
    filas_p = []
    for k in lados_p:
        nodos, cortes = [], 0
        for s in range(instancias):
            grid, a, b = cuadricula_ocupacion(k, k, DENSIDAD, semilla=7000 * k + s)
            n_con, _ = _nodos(backtracking_con_poda, grid, a, b)
            if n_con is None:
                cortes += 1
                n_con = LIMITE
            nodos.append(n_con)
        filas_p.append({"k": k, "celdas": k * k, "nodos_mediana": float(np.median(nodos)),
                        "nodos_q1": float(np.percentile(nodos, 25)), "nodos_q3": float(np.percentile(nodos, 75)),
                        "nodos_max": int(max(nodos)), "instancias_cortadas": cortes})
    guardar_csv(os.path.join(CARPETA, "c4_poda_escala.csv"), filas_p, list(filas_p[0].keys()))
    resumen["poda_escala"] = filas_p
    Vp = np.array([f["celdas"] for f in filas_p], float)
    mp = np.array([f["nodos_mediana"] for f in filas_p])
    resumen["pendiente_nodos_poda"] = pendiente_loglog(Vp, mp)[0]

    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    ax.errorbar(Vp, mp, yerr=[mp - [f["nodos_q1"] for f in filas_p], np.array([f["nodos_q3"] for f in filas_p]) - mp],
                fmt="s-", color=COLORES[0], ms=4, capsize=2,
                label=f"con poda: mediana (pend. {resumen['pendiente_nodos_poda']:.2f})")
    ax.plot(Vp, [f["nodos_max"] for f in filas_p], ":", color=COLORES[0], lw=1, label="con poda: máximo")
    ax.plot(Vp, Vp * (1 - DENSIDAD), "--", color=COLORES[2], lw=1, label="celdas libres (lo que expande BFS)")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("celdas V = k²")
    ax.set_ylabel("nodos explorados")
    ax.set_title("C4: la poda no elimina el crecimiento exponencial")
    ax.legend(fontsize=7)
    guardar(fig, "c4_poda_escala.png")

    # ---------------- Escenario: parqueadero
    grid, a, b = estacionamiento(filas_puestos=3, puestos=10, ocupacion=0.8)
    d, camino, est = backtracking_con_poda(grid, a, b)
    n_sin, _ = _nodos(backtracking_sin_poda, grid, a, b)
    d2, _, e2 = bfs(grid, a, b)
    resumen["parqueadero"] = {"longitud": d, "nodos_con_poda": est.nodos, "podas": est.podas,
                              "nodos_sin_poda": n_sin, "nodos_bfs": e2.nodos, "longitud_bfs": d2}
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.imshow(np.array(grid), cmap="Greys", vmin=0, vmax=1.6)
    ys, xs = zip(*camino)
    ax.plot(xs, ys, "-", color=COLORES[1], lw=2)
    ax.plot(a[1], a[0], "o", color=COLORES[2], ms=8, label="vehículo")
    ax.plot(b[1], b[0], "*", color=COLORES[1], ms=12, label="puesto libre")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title(f"Maniobra de parqueo: {d} movimientos")
    ax.legend(fontsize=7, loc="lower left")
    guardar(fig, "c4_parqueadero.png")

    with open(os.path.join(CARPETA, "c4_resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in resumen.items() if k not in ("pequenas", "poda_escala")},
                     indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
