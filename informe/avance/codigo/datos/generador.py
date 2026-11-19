"""Generador de datos sintéticos del Grupo 6 (semilla fija).

Escenario: un vehículo autónomo recorre una ciudad sintética de 1 km x 1 km.

- nube_puntos_2d: obstáculos detectados proyectados al plano (C1).
- escena_urbana_3d / claves_voxel: nube LiDAR 3D y su voxelización (C2).
- tramos_sensado: intervalos [a, b] que cada sensor cubre sobre la trayectoria [0, L] (C3).

Uso por consola (escribe muestras CSV en datos/muestras/):
    python -m datos.generador
"""
import math
import os

import numpy as np

SEMILLA = 6          # grupo 6
LADO_CIUDAD = 1000.0  # metros


def _rng(semilla):
    return np.random.default_rng(SEMILLA if semilla is None else semilla)


# ----------------------------------------------------------------- C1
def nube_puntos_2d(n, distribucion="uniforme", semilla=None):
    """n puntos (x, y) en [0, LADO_CIUDAD]^2 como lista de tuplas de float.

    - "uniforme": caso típico (esperado).
    - "agrupada": puntos concentrados alrededor de ~sqrt(n) obstáculos (más puntos en la franja).
    - "vertical": todos con casi la misma x -> toda la nube cae en la franja central;
      sirve para mostrar que aun así el algoritmo sigue siendo Theta(n log n).
    """
    rng = _rng(semilla)
    if distribucion == "uniforme":
        p = rng.uniform(0, LADO_CIUDAD, size=(n, 2))
    elif distribucion == "agrupada":
        k = max(1, int(math.sqrt(n)))
        centros = rng.uniform(0, LADO_CIUDAD, size=(k, 2))
        asignacion = rng.integers(0, k, size=n)
        p = centros[asignacion] + rng.normal(0, 2.0, size=(n, 2))
    elif distribucion == "vertical":
        p = np.column_stack([500.0 + rng.uniform(-1e-3, 1e-3, size=n),
                             rng.uniform(0, LADO_CIUDAD, size=n)])
    else:
        raise ValueError(distribucion)
    return [(float(x), float(y)) for x, y in p]


# ----------------------------------------------------------------- C2
def escena_urbana_3d(n_puntos, lado=64.0, semilla=None):
    """Nube LiDAR sintética de una manzana de ``lado`` metros.

    Mezcla suelo (z = 0), fachadas de edificios (caras verticales de cajas) y postes.
    Los puntos viven sobre superficies, por eso el número de vóxeles ocupados crece
    como (L/r)^2 y no como (L/r)^3: es lo que hace rentable la tabla hash.
    """
    rng = _rng(semilla)
    n_suelo = n_puntos // 2
    n_fachada = (n_puntos // 3) // 4 * 4   # múltiplo de 4: mismo número por edificio
    n_poste = n_puntos - n_suelo - n_fachada
    suelo = np.column_stack([rng.uniform(0, lado, n_suelo), rng.uniform(0, lado, n_suelo),
                             np.zeros(n_suelo)])
    # 4 edificios fijos (proporcionales al lado); se muestrean sus fachadas.
    edificios = [(0.1, 0.1, 0.35, 0.3, 0.5), (0.55, 0.1, 0.9, 0.35, 0.7),
                 (0.1, 0.6, 0.4, 0.9, 0.4), (0.6, 0.6, 0.85, 0.85, 0.6)]
    fach = []
    por_edif = n_fachada // len(edificios)
    for (x0, y0, x1, y1, h) in edificios:
        x0, y0, x1, y1, h = (v * lado for v in (x0, y0, x1, y1, h))
        cara = rng.integers(0, 4, por_edif)
        t = rng.uniform(0, 1, por_edif)
        z = rng.uniform(0, h, por_edif)
        x = np.where(cara == 0, x0, np.where(cara == 1, x1, x0 + t * (x1 - x0)))
        y = np.where(cara == 2, y0, np.where(cara == 3, y1, y0 + t * (y1 - y0)))
        fach.append(np.column_stack([x, y, z]))
    fach = np.vstack(fach) if fach else np.empty((0, 3))
    postes_xy = rng.uniform(0, lado, size=(20, 2))
    idx = rng.integers(0, 20, n_poste)
    poste = np.column_stack([postes_xy[idx], rng.uniform(0, 0.15 * lado, n_poste)])
    return np.vstack([suelo, fach, poste])


def claves_voxel(puntos, r):
    """Convierte cada punto 3D en la clave entera (i, j, k) = floor(p / r) de su vóxel."""
    ijk = np.floor(np.asarray(puntos) / r).astype(np.int64)
    return [tuple(map(int, f)) for f in ijk]


def claves_distintas(n, semilla=None):
    """n claves de vóxel distintas (para medir solo inserciones nuevas en C2)."""
    rng = _rng(semilla)
    lado = int(math.ceil(n ** (1 / 3))) * 4
    vistas = set()
    claves = []
    while len(claves) < n:
        lote = rng.integers(-lado, lado, size=(n, 3))
        for f in lote:
            t = (int(f[0]), int(f[1]), int(f[2]))
            if t not in vistas:
                vistas.add(t)
                claves.append(t)
                if len(claves) == n:
                    break
    return claves


# ----------------------------------------------------------------- C3
def tramos_sensado(n, largo=None, semilla=None):
    """n intervalos (a, b) de sensado sobre la trayectoria [0, largo].

    Se garantiza que existe cobertura: ~n/10 tramos forman una "columna" que se
    solapa de punta a punta; el resto son sensores con centro y alcance aleatorios.
    Los tramos se devuelven desordenados.
    """
    rng = _rng(semilla)
    largo = float(n) if largo is None else float(largo)
    k = max(1, n // 10)
    paso = largo / k
    columna = [(max(0.0, i * paso - rng.uniform(0, 0.2) * paso),
                min(largo, (i + 1) * paso + rng.uniform(0, 0.2) * paso)) for i in range(k)]
    resto = n - k
    centros = rng.uniform(0, largo, resto)
    alcance = rng.uniform(0.2, 3.0, resto) * paso / 2
    otros = [(float(max(0.0, c - a)), float(min(largo, c + a))) for c, a in zip(centros, alcance)]
    tramos = [(float(a), float(b)) for a, b in columna] + otros
    orden = rng.permutation(n)
    return [tramos[i] for i in orden], largo


def tramos_pequenos(n, largo=10.0, semilla=None):
    """Instancias pequeñas (n <= 15) para comparar contra fuerza bruta; pueden no ser factibles."""
    rng = _rng(semilla)
    a = rng.uniform(-1, largo, n)
    longitud = rng.uniform(1, largo / 2, n)
    return [(float(round(x, 2)), float(round(x + l, 2))) for x, l in zip(a, longitud)], largo


# ----------------------------------------------------------------- CLI
def _escribir(ruta, encabezado, filas):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(encabezado + "\n")
        for fila in filas:
            f.write(",".join(f"{v:.6f}" if isinstance(v, float) else str(v) for v in fila) + "\n")


def main():
    carpeta = os.path.join(os.path.dirname(__file__), "muestras")
    os.makedirs(carpeta, exist_ok=True)
    _escribir(os.path.join(carpeta, "puntos_2d_1000.csv"), "x,y", nube_puntos_2d(1000))
    escena = escena_urbana_3d(5000)
    _escribir(os.path.join(carpeta, "escena_3d_5000.csv"), "x,y,z",
              [tuple(map(float, p)) for p in escena])
    tramos, largo = tramos_sensado(1000)
    _escribir(os.path.join(carpeta, f"tramos_1000_L{int(largo)}.csv"), "a,b", tramos)
    print("Muestras escritas en", carpeta)


if __name__ == "__main__":
    main()
