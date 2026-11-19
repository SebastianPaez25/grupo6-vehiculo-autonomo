"""Experimento C6 - 2-aproximación de cobertura de vértices (sensores en intersecciones).

Hipótesis
  H6.1  En el 100 % de los grafos pequeños (V <= 20) se cumple |M| <= OPT <= |C| <= 2·OPT.
  H6.2  La razón medida |C|/OPT es en promedio menor que 2 en redes de calles, y alcanza
        exactamente 2 en el caso ajustado (aristas disjuntas).
  H6.3  La 2-aproximación es Theta(V + E): pendiente log-log ~1 hasta E ~ 2·10^6.
  H6.4  El óptimo por fuerza bruta crece exponencialmente con V (por eso se aproxima).

Ejecutar:  python -m experimentos.exp_c6  [--rapido]
"""
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

from c6_cobertura_vertices.cobertura_vertices import (cobertura_2_aproximada, es_cobertura,
                                                      grado_maximo_voraz, optimo_fuerza_bruta)
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import guardar_csv, medir
from datos.generador import emparejamiento_perfecto, grafo_aleatorio, grafo_calles

FORMAS_CALLES = [(3, 4), (3, 5), (4, 4), (3, 6), (4, 5)]      # V = 12, 15, 16, 18, 20


def main(rapido=False):
    resumen = {}
    reps = 3 if rapido else 5
    por_forma = 8 if rapido else 40

    # ---------------- H6.1 / H6.2 razón frente al óptimo
    filas = []
    s = 0
    for (r, c) in FORMAS_CALLES:
        for _ in range(por_forma):
            for tipo in ("calles", "aleatorio"):
                s += 1
                if tipo == "calles":
                    n, aristas = grafo_calles(r, c, semilla=s)
                else:
                    n, aristas = grafo_aleatorio(r * c, 0.25, semilla=s)
                if not aristas:
                    continue
                cob, m = cobertura_2_aproximada(n, aristas)
                opt, sol = optimo_fuerza_bruta(n, aristas, desde=len(m))
                assert es_cobertura(aristas, cob) and es_cobertura(aristas, sol)
                g = grado_maximo_voraz(n, aristas)
                filas.append({"tipo": tipo, "V": n, "E": len(aristas), "M": len(m), "OPT": opt,
                              "C": len(cob), "razon": len(cob) / opt, "grado_max": len(g),
                              "razon_grado_max": len(g) / opt})
    guardar_csv(os.path.join(CARPETA, "c6_razones.csv"), filas, list(filas[0].keys()))
    razones = np.array([f["razon"] for f in filas])
    resumen["grafos"] = len(filas)
    resumen["cumplen_M_le_OPT_le_C_le_2OPT"] = int(sum(f["M"] <= f["OPT"] <= f["C"] <= 2 * f["OPT"] for f in filas))
    resumen["razon_media"] = {t: float(np.mean([f["razon"] for f in filas if f["tipo"] == t]))
                              for t in ("calles", "aleatorio")}
    resumen["razon_max"] = float(razones.max())
    resumen["razon_min"] = float(razones.min())
    resumen["razon_media_grado_max"] = float(np.mean([f["razon_grado_max"] for f in filas]))
    n, aristas = emparejamiento_perfecto(8)
    cob, _ = cobertura_2_aproximada(n, aristas)
    resumen["caso_ajustado"] = {"C": len(cob), "OPT": optimo_fuerza_bruta(n, aristas)[0]}

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    bins = np.linspace(1, 2, 11)
    for k, t in enumerate(("calles", "aleatorio")):
        ax.hist([f["razon"] for f in filas if f["tipo"] == t], bins=bins, alpha=0.6,
                color=COLORES[k], label=f"{t} (media {resumen['razon_media'][t]:.2f})")
    ax.axvline(2, color="k", lw=1, ls="--")
    ax.text(1.98, ax.get_ylim()[1] * 0.9, "garantía: 2", ha="right", fontsize=8)
    ax.set_xlabel("|C| / OPT")
    ax.set_ylabel("grafos")
    ax.set_title(f"C6: razón medida en {len(filas)} grafos con V ≤ 20 (máx. {razones.max():.2f})")
    ax.legend(fontsize=8)
    guardar(fig, "c6_razones.png")

    # ---------------- H6.3 tiempo de la 2-aproximación
    lados = [32, 64, 128, 256] if rapido else [32, 45, 64, 90, 128, 181, 256, 362, 512, 724, 1024]
    tiempos = medir(lambda g: cobertura_2_aproximada(*g), lambda k: grafo_calles(k, k, semilla=k),
                    lados, reps)
    for f, k in zip(tiempos, lados):
        f["k"] = k
        f["V"] = k * k
        f["E"] = len(grafo_calles(k, k, semilla=k)[1])
        f["n"] = f["V"] + f["E"]
    guardar_csv(os.path.join(CARPETA, "c6_tiempo.csv"), tiempos, ["k", "V", "E", "mediana", "q1", "q3"])

    # ---------------- H6.4 fuerza bruta (exponencial)
    fb = medir(lambda g: optimo_fuerza_bruta(*g), lambda rc: grafo_calles(rc[0], rc[1], semilla=99),
               FORMAS_CALLES[:4] if rapido else FORMAS_CALLES, reps)
    for f, (r, c) in zip(fb, FORMAS_CALLES):
        f["V"] = r * c
    guardar_csv(os.path.join(CARPETA, "c6_fuerza_bruta.csv"), fb, ["V", "mediana", "q1", "q3"])
    resumen["pendiente_tiempo"] = loglog([("2-aproximación", tiempos)],
                                         "C6: tiempo de la 2-aproximación (log-log)",
                                         "c6_loglog.png", xlabel="V + E")["2-aproximación"]
    V = np.array([f["V"] for f in fb], float)
    t = np.array([f["mediana"] for f in fb])
    a, _ = np.polyfit(V, np.log(t), 1)
    resumen["factor_fuerza_bruta_por_vertice"] = float(np.exp(a))
    resumen["fuerza_bruta"] = [{"V": int(v), "s": float(x)} for v, x in zip(V, t)]

    with open(os.path.join(CARPETA, "c6_resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, indent=2, ensure_ascii=False)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
