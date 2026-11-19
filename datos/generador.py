"""Generador de datos sintéticos del Grupo 6 (semilla fija).

Escenario: un vehículo autónomo recorre una ciudad sintética de 1 km x 1 km.

- nube_puntos_2d: obstáculos detectados proyectados al plano (C1).
- escena_urbana_3d / claves_voxel: nube LiDAR 3D y su voxelización (C2).
- tramos_sensado: intervalos [a, b] que cada sensor cubre sobre la trayectoria [0, L] (C3).
- cuadricula_ocupacion / estacionamiento: cuadrículas de ocupación para planear maniobras (C4).
- telemetria: flujo de registros ordenados por marca de tiempo, sin cargarlos en memoria (C5).
- grafo_calles / grafo_aleatorio: intersecciones y calles para ubicar sensores (C6).

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


# ----------------------------------------------------------------- C4
def _hay_camino(grid, inicio, meta):
    """Relleno por inundación (solo para validar el generador; no es el algoritmo de C4)."""
    filas, cols = len(grid), len(grid[0])
    vistos = {inicio}
    pila = [inicio]
    while pila:
        r, c = pila.pop()
        if (r, c) == meta:
            return True
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = (r + dr, c + dc)
            if 0 <= v[0] < filas and 0 <= v[1] < cols and grid[v[0]][v[1]] == 0 and v not in vistos:
                vistos.add(v)
                pila.append(v)
    return False


def cuadricula_ocupacion(filas, cols, densidad=0.2, semilla=None):
    """Cuadrícula filas x cols con obstáculos aleatorios (1 = ocupado) y camino garantizado.

    Inicio = esquina (0, 0) y meta = esquina opuesta. Si la cuadrícula sorteada no tiene camino,
    se vuelve a sortear con el mismo generador (la secuencia sigue siendo reproducible).
    Devuelve (grid, inicio, meta).
    """
    rng = _rng(semilla)
    inicio, meta = (0, 0), (filas - 1, cols - 1)
    for _ in range(1000):
        m = (rng.random((filas, cols)) < densidad).astype(int)
        m[inicio] = 0
        m[meta] = 0
        grid = m.tolist()
        if _hay_camino(grid, inicio, meta):
            return grid, inicio, meta
    raise RuntimeError("no se pudo generar una cuadrícula con camino")


def estacionamiento(filas_puestos=3, puestos=10, ocupacion=0.8, semilla=None):
    """Parqueadero: hileras de puestos separadas por carriles; el vehículo entra por la esquina
    superior izquierda y debe llegar al puesto libre más alejado. Devuelve (grid, inicio, meta)."""
    rng = _rng(semilla)
    filas = 3 * filas_puestos + 1           # carril, puestos, puestos, carril, ...
    cols = puestos + 2
    grid = [[0] * cols for _ in range(filas)]
    libres = []
    for h in range(filas_puestos):
        for fila in (3 * h + 1, 3 * h + 2):
            for c in range(1, cols - 1):
                if rng.random() < ocupacion:
                    grid[fila][c] = 1
                else:
                    libres.append((fila, c))
    inicio = (0, 0)
    if not libres:
        raise RuntimeError("parqueadero lleno")
    meta = libres[-1]
    return grid, inicio, meta


# ----------------------------------------------------------------- C5
def telemetria(n, semilla=None, t0=1_700_000_000_000):
    """Genera n registros (t_ms, x, y, v, rumbo) en orden creciente de marca de tiempo.

    Es un generador: produce los registros por lotes y nunca guarda los n en memoria, para
    respetar el límite M de la memoria interna en C5. Las marcas de tiempo son únicas
    (separación de 1 a 200 ms, como un sensor a ~10 Hz con variaciones).
    """
    rng = _rng(semilla)
    t, x, y, rumbo = t0, 0.0, 0.0, 0.0
    lote = 4096
    producidos = 0
    while producidos < n:
        k = min(lote, n - producidos)
        dt = rng.integers(1, 201, size=k)
        dv = rng.normal(0, 0.5, size=k)
        dr = rng.normal(0, 0.02, size=k)
        for i in range(k):
            t += int(dt[i])
            rumbo += float(dr[i])
            v = max(0.0, min(20.0, 8.0 + float(dv[i]) * 4))
            x += v * 0.1 * math.cos(rumbo)
            y += v * 0.1 * math.sin(rumbo)
            yield (t, x, y, v, rumbo)
        producidos += k


# ----------------------------------------------------------------- C6
def grafo_calles(filas, cols, prob_calle=0.85, prob_diagonal=0.1, semilla=None):
    """Red de calles: intersecciones en una rejilla filas x cols (vértices 0..V-1) y calles entre
    intersecciones vecinas (presentes con probabilidad prob_calle) más algunas diagonales.
    Devuelve (V, lista de aristas (u, v) con u < v)."""
    rng = _rng(semilla)
    idx = lambda r, c: r * cols + c
    aristas = []
    for r in range(filas):
        for c in range(cols):
            if c + 1 < cols and rng.random() < prob_calle:
                aristas.append((idx(r, c), idx(r, c + 1)))
            if r + 1 < filas and rng.random() < prob_calle:
                aristas.append((idx(r, c), idx(r + 1, c)))
            if r + 1 < filas and c + 1 < cols and rng.random() < prob_diagonal:
                aristas.append((idx(r, c), idx(r + 1, c + 1)))
    return filas * cols, aristas


def grafo_aleatorio(n, p, semilla=None):
    """Grafo de Erdős–Rényi G(n, p). Devuelve (n, aristas)."""
    rng = _rng(semilla)
    aristas = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]
    return n, aristas


def emparejamiento_perfecto(n_aristas):
    """Caso ajustado: n aristas disjuntas. El óptimo es n y la 2-aproximación da exactamente 2n."""
    return 2 * n_aristas, [(2 * i, 2 * i + 1) for i in range(n_aristas)]


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
