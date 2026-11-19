"""Experimento C2 - mapa de vóxeles con tabla hash dinámica.

Hipótesis
  H2.1  Método contable: con c_hat = 3 por inserción el banco nunca es negativo, luego el
        costo real acumulado cumple C(n) <= 3n para todo n (de hecho 2n <= C(n) <= 3n).
  H2.2  Insertar n claves cuesta Theta(n) en total: pendiente log-log ~ 1 y tiempo por
        inserción aproximadamente constante (O(1) amortizado).
  H2.3  Espacio: los vóxeles ocupados N crecen como (L/r)^2 (superficies) y la tabla usa
        Theta(N); la rejilla densa crece como (L/r)^3. Pendientes ~2 y ~3 respecto a L/r.

Ejecutar:  python -m experimentos.exp_c2  [--rapido]
"""
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

from c2_mapa_voxeles.mapa_voxeles import (bytes_tabla, celdas_rejilla_densa, construir_mapa,
                                          unidades_espacio_tabla)
from c2_mapa_voxeles.tabla_hash import TablaHashVoxeles
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import guardar_csv, medir, pendiente_loglog, pendientes_por_rango
from datos.generador import claves_distintas, escena_urbana_3d


def _insertar_todas(claves):
    t = TablaHashVoxeles(instrumentar=False)
    for k in claves:
        t.insertar(k)
    return t


def main(rapido=False):
    resumen = {}
    k_max = 17 if rapido else 20
    reps = 3 if rapido else 5

    # ---------------- H2.2 tiempo total de n inserciones
    tam = [2 ** k for k in range(10, k_max + 1)]
    filas = medir(_insertar_todas, claves_distintas, tam, reps)
    for f in filas:
        f["us_por_insercion"] = f["mediana"] / f["n"] * 1e6
    guardar_csv(os.path.join(CARPETA, "c2_tiempo.csv"), filas,
                ["n", "mediana", "q1", "q3", "minimo", "us_por_insercion"])
    resumen["pendiente_tiempo"] = loglog([("n inserciones", filas)],
                                         "C2: tiempo total de n inserciones (log-log)",
                                         "c2_loglog.png")["n inserciones"]
    resumen["pendientes_por_rango"] = pendientes_por_rango(filas)
    resumen["us_por_insercion"] = {str(f["n"]): f["us_por_insercion"] for f in filas}

    # ---------------- H2.1 método contable (instrumentado)
    n_cont = 2 ** 16 if rapido else 2 ** 20
    t = TablaHashVoxeles(instrumentar=True)
    banco = np.empty(n_cont)
    for i, k in enumerate(claves_distintas(n_cont)):
        t.insertar(k)
        banco[i] = t.banco
    costo = np.array(t.historial, float)
    acumulado = np.cumsum(costo)
    idx = np.arange(1, n_cont + 1)
    resumen["contable"] = {
        "n": n_cont, "costo_real_total": int(acumulado[-1]), "cota_3n": 3 * n_cont,
        "max_C(n)/n": float((acumulado / idx).max()),
        "min_C(n)/n_desde_64": float((acumulado / idx)[63:].min()),
        "banco_minimo": float(banco.min()), "redimensionamientos": t.redimensionamientos,
        "capacidad_final": t.capacidad, "factor_carga_final": t.factor_carga(),
    }
    corte = 2 ** 12
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
    axs[0].vlines(idx[:corte], 0, costo[:corte], color=COLORES[0], lw=0.8)
    axs[0].set_title("costo real por inserción")
    axs[0].set_xlabel("i (primeras 4096)")
    axs[1].plot(idx, acumulado, color=COLORES[0], lw=1.2, label="costo real acumulado C(n)")
    axs[1].plot(idx, 3 * idx, "--", color=COLORES[1], lw=1, label="costo amortizado 3n")
    axs[1].plot(idx, idx, ":", color="gray", lw=1, label="n")
    axs[1].set_title("costo acumulado")
    axs[1].set_xlabel("n")
    axs[1].legend(fontsize=7)
    axs[2].plot(idx[:corte], banco[:corte], color=COLORES[2], lw=1)
    axs[2].axhline(0, color="k", lw=0.6)
    axs[2].set_title("saldo del banco de créditos")
    axs[2].set_xlabel("i (primeras 4096)")
    guardar(fig, "c2_metodo_contable.png")

    # ---------------- H2.3 espacio tabla vs rejilla densa
    lado = 64.0
    lados_r = [16, 32, 64, 128] if rapido else [16, 32, 64, 128, 256]
    filas_esp = []
    for lr in lados_r:
        r = lado / lr
        pts = escena_urbana_3d(4 * lr * lr, lado=lado)
        mapa = construir_mapa(pts, r)
        filas_esp.append({
            "L/r": lr, "r": r, "puntos": len(pts), "N_ocupados": len(mapa),
            "capacidad_m": mapa.capacidad, "unidades_tabla": unidades_espacio_tabla(mapa),
            "celdas_densa": celdas_rejilla_densa(lado, r),
            "bytes_tabla_python": bytes_tabla(mapa),
            "bytes_densa_int32": 4 * celdas_rejilla_densa(lado, r),
        })
    guardar_csv(os.path.join(CARPETA, "c2_espacio.csv"), filas_esp, list(filas_esp[0].keys()))
    x = np.array([f["L/r"] for f in filas_esp], float)
    N = np.array([f["N_ocupados"] for f in filas_esp], float)
    U = np.array([f["unidades_tabla"] for f in filas_esp], float)
    D = np.array([f["celdas_densa"] for f in filas_esp], float)
    bt = np.array([f["bytes_tabla_python"] for f in filas_esp], float)
    bd = np.array([f["bytes_densa_int32"] for f in filas_esp], float)
    resumen["espacio"] = {
        "pendiente_N_vs_L/r": pendiente_loglog(x, N)[0],
        "pendiente_tabla_vs_L/r": pendiente_loglog(x, U)[0],
        "pendiente_densa_vs_L/r": pendiente_loglog(x, D)[0],
        "pendiente_tabla_vs_N": pendiente_loglog(N, U)[0],
        "unidades_tabla_sobre_N": (U / N).tolist(),
        "bytes_por_voxel_tabla_python": (bt / N).tolist(),
        "filas": filas_esp,
    }
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    axs[0].loglog(x, D, "s-", color=COLORES[1], ms=4,
                  label=f"rejilla densa (L/r)³  (pend. {resumen['espacio']['pendiente_densa_vs_L/r']:.2f})")
    axs[0].loglog(x, U, "o-", color=COLORES[0], ms=4,
                  label=f"tabla hash m+N  (pend. {resumen['espacio']['pendiente_tabla_vs_L/r']:.2f})")
    axs[0].loglog(x, N, "^-", color=COLORES[2], ms=4,
                  label=f"vóxeles ocupados N  (pend. {resumen['espacio']['pendiente_N_vs_L/r']:.2f})")
    axs[0].set_xscale("log", base=2)
    axs[0].set_xlabel("L / r")
    axs[0].set_ylabel("unidades de espacio (celdas / entradas)")
    axs[0].set_title("Espacio abstracto")
    axs[0].legend(fontsize=7)
    axs[1].loglog(x, bd / 2 ** 20, "s-", color=COLORES[1], ms=4, label="rejilla densa int32")
    axs[1].loglog(x, bt / 2 ** 20, "o-", color=COLORES[0], ms=4, label="tabla hash (objetos Python)")
    axs[1].set_xscale("log", base=2)
    axs[1].set_xlabel("L / r")
    axs[1].set_ylabel("MiB")
    axs[1].set_title("Bytes reales (constantes de CPython)")
    axs[1].legend(fontsize=7)
    guardar(fig, "c2_espacio.png")

    with open(os.path.join(CARPETA, "c2_resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in resumen.items() if k != "espacio"}, indent=2,
                     ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
