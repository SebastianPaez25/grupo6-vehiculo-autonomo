"""C4 - Backtracking en cuadrícula de ocupación (laberinto).

Uso en el caso: planear una maniobra de parqueo o de evasión. La cuadrícula viene de
proyectar el mapa de vóxeles (C2) al plano; una celda es 1 si está ocupada y 0 si está
libre. El vehículo se mueve a las 4 celdas vecinas con costo 1 y se busca un camino
de longitud mínima del inicio a la meta.

Tres algoritmos, todos devuelven la longitud mínima (o None si no hay camino):
  - backtracking_sin_poda: recorre TODOS los caminos simples del inicio a la meta y se queda
    con el más corto. Árbol de búsqueda O(3^V) (cada celda, salvo la primera, tiene a lo
    sumo 3 vecinos no visitados).
  - backtracking_con_poda: igual, pero descarta (poda) una rama cuando
        g + manhattan(celda, meta) >= mejor_encontrado,
    donde g es la longitud del camino parcial. Como cada movimiento cambia la distancia
    Manhattan en exactamente 1, manhattan es una cota inferior del costo restante
    (admisible), así que la poda nunca descarta una solución mejor. Además prueba primero
    los vecinos más cercanos a la meta para encontrar pronto una buena cota.
  - bfs: búsqueda en anchura, Theta(V + E) = Theta(V) en una cuadrícula (E <= 2V).

Se usan pilas y colas explícitas (listas) en lugar de recursión, para no chocar con el
límite de recursión de Python en cuadrículas grandes.
"""
from comun.ordenamiento import merge_sort

MOVIMIENTOS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class LimiteExcedido(Exception):
    """Se superó el número máximo de nodos permitido (para no colgar los experimentos)."""


class Estadisticas:
    def __init__(self):
        self.nodos = 0        # nodos del árbol de búsqueda visitados (celdas a las que se entra)
        self.podas = 0        # ramas descartadas por la cota de Manhattan
        self.soluciones = 0   # caminos completos que mejoraron la mejor solución


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _vecinos(grid, celda):
    r, c = celda
    filas, cols = len(grid), len(grid[0])
    for dr, dc in MOVIMIENTOS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < filas and 0 <= nc < cols and grid[nr][nc] == 0:
            yield (nr, nc)


def _validar(grid, inicio, meta):
    for nombre, (r, c) in (("inicio", inicio), ("meta", meta)):
        if not (0 <= r < len(grid) and 0 <= c < len(grid[0])):
            raise ValueError(f"{nombre} fuera de la cuadrícula")
        if grid[r][c] != 0:
            raise ValueError(f"{nombre} está ocupado")


def _backtracking(grid, inicio, meta, podar, limite_nodos):
    _validar(grid, inicio, meta)
    est = Estadisticas()
    est.nodos = 1
    if inicio == meta:
        return 0, [inicio], est
    filas, cols = len(grid), len(grid[0])
    visitado = [[False] * cols for _ in range(filas)]
    visitado[inicio[0]][inicio[1]] = True
    mejor, mejor_camino = float("inf"), None
    camino = [inicio]

    def hijos(celda):
        vs = list(_vecinos(grid, celda))
        if podar:   # primero los vecinos más cercanos a la meta
            vs = merge_sort(vs, key=lambda v: manhattan(v, meta))
        return vs

    pila = [(hijos(inicio), 0)]          # (lista de hijos, índice del siguiente a probar)
    while pila:
        vs, k = pila[-1]
        if k == len(vs):                 # se probaron todos los hijos: retroceder
            pila.pop()
            r, c = camino.pop()
            visitado[r][c] = False
            continue
        pila[-1] = (vs, k + 1)
        sig = vs[k]
        if visitado[sig[0]][sig[1]]:
            continue
        g = len(camino)                  # longitud del camino si avanzamos a sig
        if podar and g + manhattan(sig, meta) >= mejor:
            est.podas += 1
            continue
        est.nodos += 1
        if limite_nodos is not None and est.nodos > limite_nodos:
            raise LimiteExcedido(est.nodos)
        if sig == meta:                  # camino completo: ¿mejora?
            if g < mejor:
                mejor, mejor_camino = g, camino + [meta]
                est.soluciones += 1
            continue
        camino.append(sig)
        visitado[sig[0]][sig[1]] = True
        pila.append((hijos(sig), 0))
    if mejor_camino is None:
        return None, None, est
    return mejor, mejor_camino, est


def backtracking_sin_poda(grid, inicio, meta, limite_nodos=None):
    """Explora todos los caminos simples. Devuelve (longitud, camino, estadísticas)."""
    return _backtracking(grid, inicio, meta, podar=False, limite_nodos=limite_nodos)


def backtracking_con_poda(grid, inicio, meta, limite_nodos=None):
    """Ramificación y acotamiento con la cota de Manhattan. Devuelve (longitud, camino, estadísticas)."""
    return _backtracking(grid, inicio, meta, podar=True, limite_nodos=limite_nodos)


def bfs(grid, inicio, meta):
    """Búsqueda en anchura. Devuelve (longitud, camino, estadísticas); nodos = celdas expandidas."""
    _validar(grid, inicio, meta)
    est = Estadisticas()
    filas, cols = len(grid), len(grid[0])
    padre = [[None] * cols for _ in range(filas)]
    padre[inicio[0]][inicio[1]] = inicio
    cola = [inicio]
    cabeza = 0                            # cola con índice: desencolar es O(1)
    while cabeza < len(cola):
        celda = cola[cabeza]
        cabeza += 1
        est.nodos += 1
        if celda == meta:
            camino = [celda]
            while camino[-1] != inicio:
                r, c = camino[-1]
                camino.append(padre[r][c])
            camino.reverse()
            return len(camino) - 1, camino, est
        for v in _vecinos(grid, celda):
            if padre[v[0]][v[1]] is None:
                padre[v[0]][v[1]] = celda
                cola.append(v)
    return None, None, est


def es_camino_valido(grid, camino, inicio, meta):
    """Verifica que el camino vaya de inicio a meta por celdas libres y vecinas, sin repetir."""
    if not camino or camino[0] != inicio or camino[-1] != meta:
        return False
    if len(set(camino)) != len(camino):
        return False
    for (a, b) in zip(camino, camino[1:]):
        if manhattan(a, b) != 1 or grid[b[0]][b[1]] != 0:
            return False
    return grid[inicio[0]][inicio[1]] == 0


def cuadricula_desde_voxeles(tabla, z_min, z_max):
    """Proyecta el mapa de vóxeles de C2 a una cuadrícula de ocupación 2D.

    Una celda (i, j) queda ocupada si algún vóxel (i, j, k) con z_min <= k <= z_max tiene puntos
    (la franja de alturas que choca con el vehículo). Devuelve (grid, desplazamiento_i, desplazamiento_j).
    """
    ocupadas = [(i, j) for (i, j, k), _ in tabla.items() if z_min <= k <= z_max]
    if not ocupadas:
        return [[0]], 0, 0
    i0 = min(i for i, _ in ocupadas)
    j0 = min(j for _, j in ocupadas)
    filas = max(i for i, _ in ocupadas) - i0 + 1
    cols = max(j for _, j in ocupadas) - j0 + 1
    grid = [[0] * cols for _ in range(filas)]
    for i, j in ocupadas:
        grid[i - i0][j - j0] = 1
    return grid, i0, j0
