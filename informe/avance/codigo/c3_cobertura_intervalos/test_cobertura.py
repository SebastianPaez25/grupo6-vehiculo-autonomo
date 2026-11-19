import pytest

from c3_cobertura_intervalos.cobertura import (SinCobertura, cobertura_minima, es_cobertura,
                                               optimo_fuerza_bruta, voraz_mas_largo)
from datos.generador import tramos_pequenos, tramos_sensado


def test_ejemplo_basico():
    tramos = [(0, 3), (2, 6), (1, 4), (5, 9), (8, 10), (6, 10)]
    sol = cobertura_minima(tramos, 10)
    assert es_cobertura(sol, 10) and len(sol) == 3


def test_tramos_que_solo_se_tocan():
    assert len(cobertura_minima([(5, 10), (0, 5)], 10)) == 2


def test_hueco_lanza_excepcion():
    with pytest.raises(SinCobertura) as e:
        cobertura_minima([(0, 4), (5, 10)], 10)
    assert e.value.hueco_en == 4
    with pytest.raises(SinCobertura):
        cobertura_minima([(1, 10)], 10)       # 0 no está cubierto


def test_voraz_es_optimo_contra_fuerza_bruta():
    factibles = 0
    for s in range(400):
        tramos, largo = tramos_pequenos(10, semilla=s)
        opt = optimo_fuerza_bruta(tramos, largo)
        if opt is None:
            with pytest.raises(SinCobertura):
                cobertura_minima(tramos, largo)
        else:
            factibles += 1
            sol = cobertura_minima(tramos, largo)
            assert es_cobertura(sol, largo) and len(sol) == opt
    assert factibles > 50


def test_contraejemplo_mas_largo_primero():
    tramos = [(0, 5), (5, 10), (2, 8)]
    assert len(cobertura_minima(tramos, 10)) == 2
    assert len(voraz_mas_largo(tramos, 10)) == 3


def test_instancia_grande_valida_y_lineal_en_barrido():
    tramos, largo = tramos_sensado(20000)
    c = {}
    sol = cobertura_minima(tramos, largo, c)
    assert es_cobertura(sol, largo)
    assert c["examinados"] <= len(tramos)
