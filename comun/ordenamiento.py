"""Merge sort propio (estable).

El enunciado prohíbe usar ``sorted`` en el núcleo de un componente, así que
C1, C3 y C4 ordenan con esta función.

T(n) = 2T(n/2) + Theta(n)  ->  Theta(n log n) en todos los casos (Teorema Maestro, caso 2).
"""


def merge_sort(a, key=None):
    """Devuelve una lista nueva con los elementos de ``a`` ordenados por ``key``.

    Versión ascendente (bottom-up): mezcla corridas de tamaño 1, 2, 4, ...
    Hace ceil(log2 n) pasadas, cada una Theta(n). Estable: ante empate conserva el orden
    original, porque en la mezcla se toma primero el de la izquierda.
    """
    n = len(a)
    if key is None:
        claves = list(a)
    else:
        claves = [key(x) for x in a]
    # Ordenamos índices para no evaluar key más de una vez por elemento.
    origen = list(range(n))
    destino = [0] * n
    ancho = 1
    while ancho < n:
        for inicio in range(0, n, 2 * ancho):
            medio = min(inicio + ancho, n)
            fin = min(inicio + 2 * ancho, n)
            i, j, k = inicio, medio, inicio
            while i < medio and j < fin:
                if claves[origen[j]] < claves[origen[i]]:
                    destino[k] = origen[j]
                    j += 1
                else:
                    destino[k] = origen[i]
                    i += 1
                k += 1
            while i < medio:
                destino[k] = origen[i]
                i += 1
                k += 1
            while j < fin:
                destino[k] = origen[j]
                j += 1
                k += 1
        origen, destino = destino, origen
        ancho *= 2
    return [a[i] for i in origen]
