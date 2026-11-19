"""C6 - 2-aproximación para cobertura de vértices (emparejamiento maximal).

Uso en el caso: las intersecciones son vértices y las calles aristas. Un sensor en una
intersección vigila todas las calles que llegan a ella; se busca un conjunto pequeño de
intersecciones que cubra todas las calles (cobertura de vértices, problema NP-difícil).

Algoritmo (Gavril / Garey-Johnson):
    C = {}
    para cada arista (u, v):
        si ni u ni v están en C:  C = C ∪ {u, v}      (la arista entra al emparejamiento M)
Las aristas tomadas forman un emparejamiento maximal M y |C| = 2|M|.

Garantía: |C| <= 2·OPT.
  - C es cobertura: si una arista (u, v) quedara sin cubrir, al revisarla ni u ni v estaban
    en C y se habría tomado; contradicción.
  - Las aristas de M no comparten extremos, así que cualquier cobertura (en particular la
    óptima) necesita al menos un extremo distinto por cada una: OPT >= |M|.
  - Luego |C| = 2|M| <= 2·OPT.
Tiempo Theta(V + E): un solo recorrido de las aristas con un arreglo de marcas.

Para validar: ``optimo_fuerza_bruta`` prueba subconjuntos de tamaño creciente (grafos pequeños,
V <= 20) usando máscaras de bits; empieza en la cota inferior |M|.
"""
from itertools import combinations


def cobertura_2_aproximada(n, aristas):
    """Devuelve (cobertura como lista de vértices, emparejamiento maximal M)."""
    en_c = [False] * n
    cobertura, emparejamiento = [], []
    for u, v in aristas:
        if u == v:
            raise ValueError("lazo no permitido")
        if not en_c[u] and not en_c[v]:
            en_c[u] = en_c[v] = True
            cobertura.extend((u, v))
            emparejamiento.append((u, v))
    return cobertura, emparejamiento


def es_cobertura(aristas, vertices):
    s = set(vertices)
    return all(u in s or v in s for u, v in aristas)


def es_emparejamiento_maximal(aristas, emparejamiento):
    usados = set()
    for u, v in emparejamiento:
        if u in usados or v in usados:
            return False
        usados.update((u, v))
    return all(u in usados or v in usados for u, v in aristas)


def optimo_fuerza_bruta(n, aristas, desde=0):
    """Tamaño de la cobertura mínima probando subconjuntos por tamaño creciente (exponencial).

    ``desde`` es una cota inferior conocida (p. ej. |M|) para empezar más arriba.
    Devuelve (tamaño, una cobertura óptima).
    """
    if not aristas:
        return 0, []
    mascaras = [(1 << u) | (1 << v) for u, v in aristas]
    vertices = [w for w in range(n) if any((m >> w) & 1 for m in mascaras)]
    for k in range(max(desde, 1), len(vertices) + 1):
        for sub in combinations(vertices, k):
            s = 0
            for w in sub:
                s |= 1 << w
            if all(s & m for m in mascaras):
                return k, list(sub)
    return len(vertices), vertices


def grado_maximo_voraz(n, aristas):
    """Heurística "el de mayor grado primero" (sin garantía constante: puede ser Theta(log n)·OPT).

    Solo para comparar en los experimentos. Usa una búsqueda lineal del máximo (sin heapq).
    """
    vecinos = [set() for _ in range(n)]
    for u, v in aristas:
        vecinos[u].add(v)
        vecinos[v].add(u)
    cobertura = []
    restantes = len(aristas)
    while restantes:
        w = max(range(n), key=lambda x: len(vecinos[x]))
        cobertura.append(w)
        for x in list(vecinos[w]):
            vecinos[x].discard(w)
            restantes -= 1
        vecinos[w].clear()
    return cobertura
