"""C2 - Construcción del mapa de vóxeles y comparación de espacio con la rejilla densa.

Rejilla densa de lado L y resolución r: (L/r)^3 celdas, ocupadas o no  ->  Theta((L/r)^3).
Tabla hash: solo los N vóxeles ocupados; con factor de carga entre 3/8 y 3/4 la
capacidad m cumple N < m <= 8N/3  ->  Theta(N) cubetas + N entradas = Theta(N).
En una escena urbana los puntos viven sobre superficies, así que N = Theta((L/r)^2).
"""
import math
import sys

from c2_mapa_voxeles.tabla_hash import TablaHashVoxeles


def construir_mapa(puntos, r, instrumentar=False):
    """Voxeliza una nube de puntos 3D (iterable de (x, y, z)) con resolución r."""
    tabla = TablaHashVoxeles(instrumentar=instrumentar)
    inv = 1.0 / r
    for x, y, z in puntos:
        tabla.sumar((math.floor(x * inv), math.floor(y * inv), math.floor(z * inv)))
    return tabla


def celdas_rejilla_densa(lado, r):
    """Número de celdas de una rejilla densa que cubre un cubo de lado L."""
    return math.ceil(lado / r) ** 3


def unidades_espacio_tabla(tabla):
    """Espacio abstracto de la tabla: m cubetas + N entradas (cada una clave + valor)."""
    return tabla.capacidad + len(tabla)


def bytes_tabla(tabla):
    """Bytes reales aproximados en CPython (listas, pares, tuplas y enteros)."""
    total = sys.getsizeof(tabla._cubetas)
    for cubeta in tabla._cubetas:
        total += sys.getsizeof(cubeta)
        for par in cubeta:
            total += sys.getsizeof(par) + sys.getsizeof(par[0])
            total += sum(sys.getsizeof(c) for c in par[0]) + sys.getsizeof(par[1])
    return total
