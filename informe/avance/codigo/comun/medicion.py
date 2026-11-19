"""Protocolo de medición común (sección 4.3 del enunciado).

1. time.perf_counter(), >= 5 repeticiones, mediana y dispersión (rango intercuartílico).
2. La generación de datos queda fuera del tiempo medido.
3. Pendiente en escala log-log por mínimos cuadrados.
4. Para n log n se reporta además T(n) / (n log2 n).
"""
import gc
import math
import os
import time

import numpy as np


def medir(funcion, generar, tamanos, repeticiones=5, preparar=None):
    """Mide ``funcion(datos)`` para cada n en ``tamanos``.

    ``generar(n)`` produce los datos (no se cronometra). Si ``preparar`` existe,
    se llama antes de cada repetición para obtener una copia fresca (p. ej. una
    tabla vacía), también fuera del cronómetro.
    Devuelve una lista de dicts con n, mediana, q1, q3, minimo y los tiempos crudos.
    """
    filas = []
    for n in tamanos:
        datos = generar(n)
        tiempos = []
        for _ in range(repeticiones):
            entrada = preparar(datos) if preparar else datos
            gc.collect()
            gc.disable()
            t0 = time.perf_counter()
            funcion(entrada)
            t1 = time.perf_counter()
            gc.enable()
            tiempos.append(t1 - t0)
        t = np.array(tiempos)
        filas.append({
            "n": n,
            "mediana": float(np.median(t)),
            "q1": float(np.percentile(t, 25)),
            "q3": float(np.percentile(t, 75)),
            "minimo": float(t.min()),
            "tiempos": tiempos,
        })
    return filas


def pendiente_loglog(xs, ys):
    """Pendiente e intercepto del ajuste log(y) = m log(x) + c (mínimos cuadrados)."""
    m, c = np.polyfit(np.log(np.asarray(xs, float)), np.log(np.asarray(ys, float)), 1)
    return float(m), float(c)


def razon_nlogn(ns, ts):
    """T(n) / (n log2 n) para verificar que tiende a una constante."""
    return [t / (n * math.log2(n)) for n, t in zip(ns, ts)]


def guardar_csv(ruta, filas, columnas):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(",".join(columnas) + "\n")
        for fila in filas:
            f.write(",".join(_fmt(fila[c]) for c in columnas) + "\n")


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def pendientes_por_rango(filas, corte=2 ** 14):
    """Pendiente log-log en n <= corte (datos caben en caché) y en n >= corte (no caben)."""
    ns = [f["n"] for f in filas]
    ts = [f["mediana"] for f in filas]
    bajo = [(n, t) for n, t in zip(ns, ts) if n <= corte and n >= 2 ** 10]
    alto = [(n, t) for n, t in zip(ns, ts) if n >= corte]
    res = {}
    if len(bajo) >= 3:
        res[f"n<=2^{corte.bit_length() - 1}"] = pendiente_loglog(*zip(*bajo))[0]
    if len(alto) >= 3:
        res[f"n>=2^{corte.bit_length() - 1}"] = pendiente_loglog(*zip(*alto))[0]
    return res


def pendiente_teorica_nlogn(ns):
    """Pendiente log-log que tendría exactamente n log2 n en esos mismos tamaños (no es 1)."""
    return pendiente_loglog(ns, [n * math.log2(n) for n in ns])[0]
