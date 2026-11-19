"""C1 - Par de puntos más cercanos en 2D por divide y vencerás.

Uso en el caso: distancia mínima entre obstáculos detectados por el vehículo.

Algoritmo (Shamos-Hoey / CLRS 33.4):
  1. Ordenar una sola vez por x (merge sort propio): Theta(n log n).
  2. Recursión sobre la lista ordenada por x. Cada llamada devuelve también sus
     puntos ordenados por y, obtenidos MEZCLANDO las dos mitades (Theta(n), sin reordenar).
     Así la recurrencia que sale del código es exactamente
         T(n) = 2 T(n/2) + Theta(n)   ->   Theta(n log n)   (Teorema Maestro, caso 2).
  3. Franja de ancho 2d alrededor de la recta divisoria: cada punto se compara
     con los siguientes en y mientras dy < d; por el argumento de empaquetamiento
     son a lo sumo 7 comparaciones por punto.

Se trabaja con distancias al cuadrado para no calcular raíces en el ciclo.
"""
import math

from comun.ordenamiento import merge_sort


class Contador:
    """Cuenta operaciones elementales, independientes de la máquina."""

    def __init__(self):
        self.distancias = 0          # distancias calculadas (todas)
        self.combinacion = 0         # puntos procesados en mezcla por y + filtrado de franja
        self.comparaciones_franja = 0
        self.max_por_punto_franja = 0  # máximo de vecinos revisados por un punto de la franja


def _d2(p, q):
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return dx * dx + dy * dy


def fuerza_bruta(puntos, contador=None):
    """Theta(n²): compara los n(n-1)/2 pares. Devuelve (distancia, p, q)."""
    n = len(puntos)
    if n < 2:
        raise ValueError("se necesitan al menos 2 puntos")
    mejor = math.inf
    par = (None, None)
    for i in range(n - 1):
        pi = puntos[i]
        for j in range(i + 1, n):
            d = _d2(pi, puntos[j])
            if d < mejor:
                mejor = d
                par = (pi, puntos[j])
    if contador is not None:
        contador.distancias += n * (n - 1) // 2
    return math.sqrt(mejor), par[0], par[1]


def par_mas_cercano(puntos, contador=None):
    """Theta(n log n) por divide y vencerás. Devuelve (distancia, p, q)."""
    if len(puntos) < 2:
        raise ValueError("se necesitan al menos 2 puntos")
    px = merge_sort(puntos, key=lambda p: (p[0], p[1]))
    d2, p, q, _ = _recursivo(px, 0, len(px), contador)
    return math.sqrt(d2), p, q


def _recursivo(px, lo, hi, contador):
    """Resuelve px[lo:hi] (ordenado por x). Devuelve (d², p, q, puntos ordenados por y)."""
    n = hi - lo
    # Caso base: n <= 3 -> fuerza bruta en tiempo constante.
    if n <= 3:
        mejor, par = math.inf, (None, None)
        for i in range(lo, hi):
            for j in range(i + 1, hi):
                d = _d2(px[i], px[j])
                if d < mejor:
                    mejor, par = d, (px[i], px[j])
        if contador is not None:
            contador.distancias += n * (n - 1) // 2
        por_y = _ordenar_pequeno_por_y(px[lo:hi])
        return mejor, par[0], par[1], por_y

    # Dividir
    mid = (lo + hi) // 2
    x_medio = px[mid][0]
    # Conquistar: 2 subproblemas de tamaño n/2  ->  a = 2, b = 2
    d_izq, p1, q1, y_izq = _recursivo(px, lo, mid, contador)
    d_der, p2, q2, y_der = _recursivo(px, mid, hi, contador)
    if d_izq <= d_der:
        d2, mejor_par = d_izq, (p1, q1)
    else:
        d2, mejor_par = d_der, (p2, q2)

    # Combinar, f(n) = Theta(n): (a) mezcla por y, (b) franja, (c) barrido de la franja.
    por_y = _mezclar_por_y(y_izq, y_der)
    d = math.sqrt(d2)
    franja = [p for p in por_y if abs(p[0] - x_medio) < d]
    m = len(franja)
    if contador is not None:
        contador.combinacion += 2 * n      # n al mezclar + n al filtrar: el f(n) = Theta(n)
    for i in range(m - 1):
        pi = franja[i]
        j = i + 1
        revisados = 0
        while j < m and franja[j][1] - pi[1] < d:
            dd = _d2(pi, franja[j])
            revisados += 1
            if dd < d2:
                d2, mejor_par = dd, (pi, franja[j])
                d = math.sqrt(d2)
            j += 1
        if contador is not None:
            contador.distancias += revisados
            contador.comparaciones_franja += revisados
            if revisados > contador.max_por_punto_franja:
                contador.max_por_punto_franja = revisados
    return d2, mejor_par[0], mejor_par[1], por_y


def _mezclar_por_y(a, b):
    """Mezcla de dos listas ya ordenadas por y: Theta(len(a) + len(b))."""
    res = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i][1] <= b[j][1]:
            res.append(a[i])
            i += 1
        else:
            res.append(b[j])
            j += 1
    res.extend(a[i:])
    res.extend(b[j:])
    return res


def _ordenar_pequeno_por_y(lista):
    """Inserción para a lo sumo 3 elementos (tiempo constante)."""
    res = list(lista)
    for i in range(1, len(res)):
        x = res[i]
        j = i - 1
        while j >= 0 and res[j][1] > x[1]:
            res[j + 1] = res[j]
            j -= 1
        res[j + 1] = x
    return res
