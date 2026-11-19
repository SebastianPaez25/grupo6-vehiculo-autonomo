import pytest

from c6_cobertura_vertices.cobertura_vertices import (cobertura_2_aproximada, es_cobertura,
                                                      es_emparejamiento_maximal,
                                                      grado_maximo_voraz, optimo_fuerza_bruta)
from datos.generador import emparejamiento_perfecto, grafo_aleatorio, grafo_calles


def test_es_cobertura_y_emparejamiento_maximal():
    for s in range(30):
        n, aristas = grafo_calles(6, 7, semilla=s)
        c, m = cobertura_2_aproximada(n, aristas)
        assert es_cobertura(aristas, c)
        assert es_emparejamiento_maximal(aristas, m)
        assert len(c) == 2 * len(m)


def test_razon_a_lo_sumo_2_contra_fuerza_bruta():
    for s in range(60):
        if s % 2:
            n, aristas = grafo_calles(3, 4 + s % 3, semilla=s)
        else:
            n, aristas = grafo_aleatorio(10 + s % 5, 0.3, semilla=s)
        c, m = cobertura_2_aproximada(n, aristas)
        opt, sol = optimo_fuerza_bruta(n, aristas, desde=len(m))
        assert es_cobertura(aristas, sol)
        assert len(m) <= opt <= len(c) <= 2 * opt


def test_fuerza_bruta_conocidos():
    estrella = [(0, i) for i in range(1, 6)]
    assert optimo_fuerza_bruta(6, estrella)[0] == 1
    ciclo5 = [(i, (i + 1) % 5) for i in range(5)]
    assert optimo_fuerza_bruta(5, ciclo5)[0] == 3
    assert optimo_fuerza_bruta(3, [])[0] == 0


def test_caso_ajustado_razon_exactamente_2():
    n, aristas = emparejamiento_perfecto(6)
    c, _ = cobertura_2_aproximada(n, aristas)
    assert len(c) == 12 and optimo_fuerza_bruta(n, aristas)[0] == 6


def test_grado_maximo_es_cobertura_y_lazo_invalido():
    n, aristas = grafo_calles(5, 5, semilla=1)
    assert es_cobertura(aristas, grado_maximo_voraz(n, aristas))
    with pytest.raises(ValueError):
        cobertura_2_aproximada(2, [(1, 1)])
