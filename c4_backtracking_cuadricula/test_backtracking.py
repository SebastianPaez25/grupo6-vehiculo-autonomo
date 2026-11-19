import pytest

from c4_backtracking_cuadricula.backtracking import (LimiteExcedido, backtracking_con_poda,
                                                     backtracking_sin_poda, bfs,
                                                     cuadricula_desde_voxeles, es_camino_valido)
from c2_mapa_voxeles.mapa_voxeles import construir_mapa
from datos.generador import cuadricula_ocupacion, escena_urbana_3d, estacionamiento


def test_los_tres_dan_la_misma_longitud_minima():
    for s in range(60):
        k = 3 + s % 4                                   # 3x3 a 6x6
        grid, ini, fin = cuadricula_ocupacion(k, k, 0.25, semilla=s)
        d_bfs, cam_bfs, _ = bfs(grid, ini, fin)
        d_sp, cam_sp, _ = backtracking_sin_poda(grid, ini, fin)
        d_cp, cam_cp, _ = backtracking_con_poda(grid, ini, fin)
        assert d_bfs == d_sp == d_cp
        for cam in (cam_bfs, cam_sp, cam_cp):
            assert es_camino_valido(grid, cam, ini, fin) and len(cam) - 1 == d_bfs


def test_poda_explora_menos_nodos():
    grid, ini, fin = cuadricula_ocupacion(6, 6, 0.2, semilla=11)
    _, _, sin = backtracking_sin_poda(grid, ini, fin)
    _, _, con = backtracking_con_poda(grid, ini, fin)
    assert con.nodos < sin.nodos
    assert con.podas > 0


def test_cuadricula_abierta_mejor_caso_poda():
    k = 12
    grid = [[0] * k for _ in range(k)]
    d, _, est = backtracking_con_poda(grid, (0, 0), (k - 1, k - 1))
    assert d == 2 * (k - 1)
    assert est.nodos == 2 * (k - 1) + 1          # solo el primer camino: Theta(d) nodos


def test_sin_camino_y_casos_borde():
    grid = [[0, 1, 0],
            [0, 1, 0],
            [0, 1, 0]]
    assert bfs(grid, (0, 0), (0, 2))[0] is None
    assert backtracking_sin_poda(grid, (0, 0), (0, 2))[0] is None
    assert backtracking_con_poda(grid, (0, 0), (0, 2))[0] is None
    assert bfs(grid, (1, 0), (1, 0))[0] == 0
    with pytest.raises(ValueError):
        bfs(grid, (0, 1), (0, 0))


def test_limite_de_nodos():
    grid = [[0] * 7 for _ in range(7)]
    with pytest.raises(LimiteExcedido):
        backtracking_sin_poda(grid, (0, 0), (6, 6), limite_nodos=1000)


def test_estacionamiento_y_proyeccion_desde_c2():
    grid, ini, fin = estacionamiento(semilla=3)
    d, cam, _ = backtracking_con_poda(grid, ini, fin)
    assert d == bfs(grid, ini, fin)[0] and es_camino_valido(grid, cam, ini, fin)
    mapa = construir_mapa(escena_urbana_3d(20000), r=2.0)
    g2, _, _ = cuadricula_desde_voxeles(mapa, z_min=1, z_max=1)
    assert len(g2) > 1 and any(1 in fila for fila in g2)
