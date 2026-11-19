import random

from comun.ordenamiento import merge_sort


def test_ordena_como_referencia():
    rng = random.Random(6)
    for n in [0, 1, 2, 3, 7, 64, 1000]:
        a = [rng.randint(-50, 50) for _ in range(n)]
        assert merge_sort(a) == sorted(a)   # sorted solo como referencia


def test_es_estable():
    a = [(1, "a"), (0, "b"), (1, "c"), (0, "d")]
    assert merge_sort(a, key=lambda t: t[0]) == [(0, "b"), (0, "d"), (1, "a"), (1, "c")]
