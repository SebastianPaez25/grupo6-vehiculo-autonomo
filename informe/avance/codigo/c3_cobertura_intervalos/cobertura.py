"""C3 - Voraz: cobertura mínima del segmento [0, L] con intervalos.

Uso en el caso: cubrir la trayectoria [0, L] del vehículo con el mínimo número de
tramos de sensado [a_i, b_i] (intervalos cerrados).

Regla voraz: estando cubierto [0, x], entre los tramos que empiezan en a_i <= x
elegir el que llega más lejos (máximo b_i). Repetir hasta x >= L.

Costo: ordenar por a (merge sort propio) Theta(n log n) + un barrido Theta(n), porque el
índice i nunca retrocede: cada tramo se examina una sola vez.

También se incluyen, solo para validar:
  - ``optimo_fuerza_bruta``: prueba todos los subconjuntos por tamaño creciente (n <= 15).
  - ``voraz_mas_largo``: regla voraz alternativa (el tramo más largo primero), que NO es
    óptima; sirve de contraejemplo.
"""
from itertools import combinations

from comun.ordenamiento import merge_sort


class SinCobertura(Exception):
    """No existe cobertura: hay un hueco que ningún tramo cubre."""

    def __init__(self, hueco_en):
        super().__init__(f"hueco sin cubrir a partir de x = {hueco_en}")
        self.hueco_en = hueco_en


def cobertura_minima(tramos, largo, contador=None):
    """Devuelve la lista de tramos elegidos (en orden de recorrido).

    Lanza SinCobertura si [0, largo] no se puede cubrir.
    ``contador`` (dict opcional) recibe los tramos examinados en el barrido.
    """
    ordenados = merge_sort(tramos, key=lambda t: t[0])
    return barrido_voraz(ordenados, largo, contador)


def barrido_voraz(ordenados, largo, contador=None):
    """Fase lineal del voraz sobre tramos ya ordenados por inicio a (requiere largo > 0)."""
    if largo <= 0:
        raise ValueError("largo debe ser positivo")
    elegidos = []
    x = 0.0                  # invariante: [0, x] ya está cubierto por ``elegidos``
    i, n = 0, len(ordenados)
    while x < largo:
        mejor_fin, mejor = x, None
        # candidatos: tramos que empiezan dentro de lo ya cubierto (a <= x)
        while i < n and ordenados[i][0] <= x:
            if ordenados[i][1] > mejor_fin:
                mejor_fin, mejor = ordenados[i][1], ordenados[i]
            i += 1
        if mejor is None:        # nadie avanza más allá de x: hay un hueco
            raise SinCobertura(x)
        elegidos.append(mejor)
        x = mejor_fin
    if contador is not None:
        contador["examinados"] = i
    return elegidos


def es_cobertura(tramos, largo):
    """Verifica que la unión de ``tramos`` contenga [0, largo] (intervalos cerrados, largo > 0)."""
    x = 0.0
    for a, b in merge_sort(tramos, key=lambda t: t[0]):
        if a > x:
            break
        x = max(x, b)
    return x >= largo


def optimo_fuerza_bruta(tramos, largo):
    """Tamaño mínimo de una cobertura probando subconjuntos (exponencial; n <= 15).

    Devuelve None si no existe cobertura.
    """
    for k in range(1, len(tramos) + 1):
        for sub in combinations(tramos, k):
            if es_cobertura(list(sub), largo):
                return k
    return None


def voraz_mas_largo(tramos, largo):
    """Heurística NO óptima: toma tramos de mayor a menor longitud hasta cubrir.

    Descarta los que no aportan cobertura nueva. Devuelve los elegidos o None.
    """
    por_longitud = merge_sort(tramos, key=lambda t: -(t[1] - t[0]))
    elegidos = []
    for t in por_longitud:
        if es_cobertura(elegidos, largo):
            break
        if not _contenido_en_union(t, elegidos):
            elegidos.append(t)
    return elegidos if es_cobertura(elegidos, largo) else None


def _contenido_en_union(t, tramos):
    """¿El tramo t ya está contenido en la unión de ``tramos``? (para no tomar inútiles)."""
    a, b = t
    x = a
    for c, d in merge_sort(tramos, key=lambda s: s[0]):
        if c > x:
            break
        x = max(x, d)
    return x >= b
