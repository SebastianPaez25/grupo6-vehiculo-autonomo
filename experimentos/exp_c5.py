"""Experimento C5 - árbol B+ en disco para el historial de telemetría.

Parámetros del modelo de memoria externa: N registros, B registros por bloque, M registros de
memoria interna (M = N/20, de modo que los datos no caben en memoria; el árbol usa h + 2 bloques).

Hipótesis (E/S contadas frente a E/S predichas)
  H5.1  Carga masiva: lecturas = 1 + ceil(N/B_log) y escrituras = L + I_1 + ... + 1 exactamente;
        Theta(N/B): pendiente log-log ~1 de E/S y de tiempo frente a N.
  H5.2  Búsqueda puntual: lecturas = h = 1 + ceil(log_f ceil(N/b)) exactamente.
  H5.3  Rango con k resultados: (h-1) + ceil(k/b) <= lecturas <= h + ceil(k/b); para k pequeño
        cuesta ~h lecturas frente a ceil(N/B) de recorrer todo el archivo.
  H5.4  Con bloques más grandes, h baja (h ~ log_B N) y las lecturas de un rango bajan como k/B.
  H5.5  Inserción tardía: lecturas = h siempre; escrituras = 1 + 2s + [raíz dividida].

Ejecutar:  python -m experimentos.exp_c5  [--rapido]
"""
import json
import math
import os
import random
import shutil
import sys
import tempfile

import matplotlib.pyplot as plt
import numpy as np

from c5_arbol_bmas_disco.arbol_bmas import (ArbolBMas, ArchivoTelemetria, altura_predicha,
                                            escrituras_carga_masiva_predichas)
from c5_arbol_bmas_disco.disco_simulado import DiscoSimulado
from comun.graficas import CARPETA, COLORES, guardar, loglog
from comun.medicion import guardar_csv, medir, pendiente_loglog
from datos.generador import telemetria

BLOQUE = 4096


class _Escenario:
    """Archivo de telemetría de N registros en un disco simulado (la 'generación de datos')."""

    def __init__(self, carpeta, n, bloque=BLOQUE):
        self.carpeta, self.n, self.bloque = carpeta, n, bloque
        self.log = DiscoSimulado(os.path.join(carpeta, f"log_{n}_{bloque}.bin"), bloque)
        self.archivo = ArchivoTelemetria(self.log)
        self.archivo.escribir(telemetria(n, semilla=6))
        self._disco = None

    def construir(self, llenado=1.0):
        """Construye el árbol en un disco nuevo (borra el anterior para no llenar el disco real)."""
        ruta = os.path.join(self.carpeta, f"arbol_{self.n}_{self.bloque}.bin")
        if self._disco is not None:
            self._disco.cerrar()
        if os.path.exists(ruta):
            os.remove(ruta)
        self.archivo._cabecera_leida = False
        self.log.reiniciar_contadores()
        disco = DiscoSimulado(ruta, self.bloque)
        self._disco = disco
        arbol = ArbolBMas.carga_masiva(disco, self.archivo, llenado=llenado,
                                       memoria_registros=self.n // 20)
        return disco, arbol

    def marcas(self):
        """Marcas de tiempo (solo para escoger consultas en el experimento; no cuenta E/S)."""
        lect = self.log.lecturas
        self.archivo._cabecera_leida = False
        ts = np.fromiter((r[0] for r in self.archivo.leer()), dtype=np.int64, count=self.n)
        self.log.lecturas = lect
        return ts


def main(rapido=False):
    resumen = {}
    reps = 3 if rapido else 5
    tamanos = [100_000, 200_000, 400_000] if rapido else [100_000, 158_489, 251_189, 398_107, 630_957, 1_000_000]
    carpeta = tempfile.mkdtemp(prefix="c5_")
    try:
        # ---------------- H5.1 / H5.2 construcción y búsqueda puntual frente a N
        filas = []
        escenarios = {}
        for n in tamanos:
            esc = _Escenario(carpeta, n)
            escenarios[n] = esc
            disco, arbol = esc.construir()
            b, f = arbol.registros_por_hoja, arbol.hijos_por_nodo
            fila = {
                "N": n, "M": n // 20, "B_hoja": arbol.B, "F": arbol.F, "M_sobre_B": (n // 20) // arbol.B,
                "bloques_en_memoria": arbol.bloques_en_memoria_max(),
                "h": arbol.altura, "h_predicha": altura_predicha(n, b, f), "hojas": arbol.hojas,
                "lect_carga": esc.log.lecturas, "lect_carga_pred": 1 + math.ceil(n / esc.archivo.B),
                "escr_carga": disco.escrituras, "escr_carga_pred": escrituras_carga_masiva_predichas(n, b, f),
            }
            ts = esc.marcas()
            rng = random.Random(n)
            lect = []
            for t in (int(ts[rng.randrange(n)]) for _ in range(200)):
                disco.reiniciar_contadores()
                assert arbol.buscar(t) is not None
                lect.append(disco.lecturas)
            fila["lect_puntual_min"], fila["lect_puntual_max"] = min(lect), max(lect)
            fila["recorrido_completo"] = math.ceil(n / esc.archivo.B)
            filas.append(fila)
            disco.cerrar()

        tiempos = medir(lambda e: e.construir(), lambda n: escenarios[n], tamanos, reps)
        for f, t in zip(filas, tiempos):
            f["t_carga_s"] = t["mediana"]
        guardar_csv(os.path.join(CARPETA, "c5_construccion.csv"), filas, list(filas[0].keys()))
        resumen["construccion"] = filas
        resumen["carga_exacta"] = all(f["lect_carga"] == f["lect_carga_pred"] and
                                      f["escr_carga"] == f["escr_carga_pred"] for f in filas)
        resumen["puntual_exacta"] = all(f["lect_puntual_min"] == f["lect_puntual_max"] == f["h"] ==
                                        f["h_predicha"] for f in filas)
        resumen["pendiente_tiempo_carga"] = loglog(
            [("carga masiva", tiempos)], "C5: tiempo de carga masiva vs N (log-log)",
            "c5_carga_loglog.png", xlabel="N (registros)")["carga masiva"]
        resumen["pendiente_es_carga"] = pendiente_loglog(
            [f["N"] for f in filas], [f["lect_carga"] + f["escr_carga"] for f in filas])[0]

        # ---------------- H5.3 consultas por rango frente a k (N máximo)
        n = tamanos[-1]
        esc = escenarios[n]
        disco, arbol = esc.construir()
        ts = esc.marcas()
        b, h = arbol.registros_por_hoja, arbol.altura
        rng = random.Random(6)
        filas_k = []
        for k in [1, 10, 100, 1_000, 10_000, 100_000]:
            lect = []
            for _ in range(50):
                i = rng.randrange(n - k + 1)
                disco.reiniciar_contadores()
                cont = arbol.contar_rango(int(ts[i]), int(ts[i + k - 1]))
                assert cont == k
                lect.append(disco.lecturas)
            filas_k.append({"k": k, "lect_min": min(lect), "lect_mediana": float(np.median(lect)),
                            "lect_max": max(lect), "pred_inferior": h - 1 + math.ceil(k / b),
                            "pred_superior": h + math.ceil(k / b),
                            "dentro": all(h - 1 + math.ceil(k / b) <= x <= h + math.ceil(k / b) for x in lect),
                            "recorrido_completo": math.ceil(n / esc.archivo.B)})
        guardar_csv(os.path.join(CARPETA, "c5_rangos.csv"), filas_k, list(filas_k[0].keys()))
        resumen["rangos"] = filas_k
        resumen["rangos_dentro_de_la_formula"] = all(f["dentro"] for f in filas_k)
        disco.cerrar()

        fig, ax = plt.subplots(figsize=(6.2, 3.9))
        ks = np.array([f["k"] for f in filas_k], float)
        ax.fill_between(ks, [f["pred_inferior"] for f in filas_k], [f["pred_superior"] for f in filas_k],
                        color=COLORES[0], alpha=0.15, label="predicho: (h−1)+⌈k/b⌉ a h+⌈k/b⌉")
        ax.errorbar(ks, [f["lect_mediana"] for f in filas_k],
                    yerr=[np.array([f["lect_mediana"] - f["lect_min"] for f in filas_k]),
                          np.array([f["lect_max"] - f["lect_mediana"] for f in filas_k])],
                    fmt="o", color=COLORES[0], ms=4, capsize=2, label="contado (mediana, mín–máx)")
        ax.axhline(filas_k[0]["recorrido_completo"], ls="--", color=COLORES[1], lw=1,
                   label=f"recorrer todo el archivo: ⌈N/B⌉ = {filas_k[0]['recorrido_completo']}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("k (registros en el rango)")
        ax.set_ylabel("lecturas de bloque")
        ax.set_title(f"C5: consultas por rango, N = {n:,} (h = {h}, b = {b})".replace(",", "."))
        ax.legend(fontsize=7)
        guardar(fig, "c5_rangos.png")

        # ---------------- H5.4 efecto del tamaño de bloque (N máximo)
        filas_b = []
        for bloque in ([1024, 4096] if rapido else [512, 1024, 2048, 4096, 8192]):
            e2 = esc if bloque == BLOQUE else _Escenario(carpeta, n, bloque)
            d2, a2 = e2.construir()
            ts2 = e2.marcas() if bloque != BLOQUE else ts
            rng = random.Random(bloque)
            k = 10_000
            lect_r, lect_p = [], []
            for _ in range(30):
                i = rng.randrange(n - k + 1)
                d2.reiniciar_contadores()
                a2.contar_rango(int(ts2[i]), int(ts2[i + k - 1]))
                lect_r.append(d2.lecturas)
                d2.reiniciar_contadores()
                a2.buscar(int(ts2[i]))
                lect_p.append(d2.lecturas)
            filas_b.append({"bloque_bytes": bloque, "b": a2.registros_por_hoja, "f": a2.hijos_por_nodo,
                            "h": a2.altura, "h_predicha": altura_predicha(n, a2.registros_por_hoja, a2.hijos_por_nodo),
                            "lect_puntual": float(np.median(lect_p)),
                            "lect_rango_10k_mediana": float(np.median(lect_r)),
                            "pred_rango_sup": a2.altura + math.ceil(k / a2.registros_por_hoja)})
            d2.cerrar()
        guardar_csv(os.path.join(CARPETA, "c5_tamano_bloque.csv"), filas_b, list(filas_b[0].keys()))
        resumen["tamano_bloque"] = filas_b

        # ---------------- H5.5 inserción de registros tardíos
        n_ins = 100_000
        filas_ins = []
        for llenado in (1.0, 0.7):
            e3 = escenarios[tamanos[0]] if tamanos[0] == n_ins else _Escenario(carpeta, n_ins)
            d3, a3 = e3.construir(llenado=llenado)
            ts3 = set(int(t) for t in e3.marcas())
            rng = random.Random(int(llenado * 10))
            lect, escr, exactas, insertados = [], [], 0, 0
            lo, hi = min(ts3), max(ts3)
            while insertados < (300 if rapido else 2000):
                t = rng.randint(lo, hi)
                if t in ts3:
                    continue
                h0, raiz0 = a3.altura, a3.raiz
                hojas0 = a3.hojas
                d3.reiniciar_contadores()
                assert a3.insertar((t, 0.0, 0.0, 0.0, 0.0))
                ts3.add(t)
                insertados += 1
                lect.append(d3.lecturas)
                escr.append(d3.escrituras)
                s = (d3.escrituras - 1 - (a3.raiz != raiz0)) // 2
                exactas += (d3.lecturas == h0 and d3.escrituras == 1 + 2 * s + (a3.raiz != raiz0)
                            and (s >= 1) == (a3.hojas > hojas0))
            filas_ins.append({"llenado": llenado, "inserciones": insertados, "h": a3.altura,
                              "lecturas_por_insercion": float(np.mean(lect)),
                              "escrituras_por_insercion": float(np.mean(escr)),
                              "fraccion_con_division": float(np.mean([e > 1 for e in escr])),
                              "formula_exacta_en": exactas})
            a3.validar()
            d3.cerrar()
        guardar_csv(os.path.join(CARPETA, "c5_inserciones.csv"), filas_ins, list(filas_ins[0].keys()))
        resumen["inserciones"] = filas_ins
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)

    with open(os.path.join(CARPETA, "c5_resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in resumen.items() if k in (
        "carga_exacta", "puntual_exacta", "pendiente_tiempo_carga", "pendiente_es_carga",
        "rangos_dentro_de_la_formula", "inserciones")}, indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
