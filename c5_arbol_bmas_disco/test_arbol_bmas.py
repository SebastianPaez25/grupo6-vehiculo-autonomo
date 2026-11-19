import math
import random

import pytest

from c5_arbol_bmas_disco.arbol_bmas import (ArbolBMas, ArchivoTelemetria, MemoriaInsuficiente,
                                            altura_predicha, capacidad_hoja,
                                            escrituras_carga_masiva_predichas)
from c5_arbol_bmas_disco.disco_simulado import DiscoSimulado
from datos.generador import telemetria


def _construir(tmp_path, n, bloque=512, llenado=1.0, memoria=None):
    log = DiscoSimulado(str(tmp_path / f"log_{n}_{bloque}.bin"), bloque)
    archivo = ArchivoTelemetria(log)
    archivo.escribir(telemetria(n, semilla=n))
    log.reiniciar_contadores()
    disco = DiscoSimulado(str(tmp_path / f"arbol_{n}_{bloque}.bin"), bloque)
    arbol = ArbolBMas.carga_masiva(disco, archivo, llenado=llenado, memoria_registros=memoria)
    return log, archivo, disco, arbol


def test_disco_cuenta_lecturas_y_escrituras(tmp_path):
    d = DiscoSimulado(str(tmp_path / "d.bin"), 128)
    d.escribir_bloque(0, b"hola")
    d.escribir_bloque(3, b"x")                  # crece el archivo
    assert d.leer_bloque(0)[:4] == b"hola" and len(d.leer_bloque(3)) == 128
    assert d.contadores() == (2, 2) and d.num_bloques == 4
    with pytest.raises(IndexError):
        d.leer_bloque(4)
    with pytest.raises(ValueError):
        d.escribir_bloque(1, b"y" * 129)
    d.cerrar()


@pytest.mark.parametrize("n", [1, 20, 21, 1000, 30000])
def test_carga_masiva_formulas_exactas(tmp_path, n):
    log, archivo, disco, arbol = _construir(tmp_path, n)
    assert arbol.validar()
    b, f = arbol.registros_por_hoja, arbol.hijos_por_nodo
    assert log.lecturas == 1 + math.ceil(n / archivo.B)
    assert disco.escrituras == escrituras_carga_masiva_predichas(n, b, f)
    assert arbol.altura == altura_predicha(n, b, f)


def test_busqueda_puntual_cuesta_h_lecturas(tmp_path):
    log, archivo, disco, arbol = _construir(tmp_path, 20000)
    ts = [r[0] for r in archivo.leer()]
    for t in random.Random(1).sample(ts, 100):
        disco.reiniciar_contadores()
        assert arbol.buscar(t)[0] == t
        assert disco.lecturas == arbol.altura
    disco.reiniciar_contadores()
    assert arbol.buscar(ts[0] - 5) is None and disco.lecturas == arbol.altura


def test_rango_correcto_y_dentro_de_la_formula(tmp_path):
    log, archivo, disco, arbol = _construir(tmp_path, 20000)
    ts = [r[0] for r in archivo.leer()]
    rng = random.Random(2)
    b, h = arbol.registros_por_hoja, arbol.altura
    for _ in range(200):
        i = rng.randrange(len(ts))
        j = min(len(ts) - 1, i + rng.choice([0, 5, 50, 500, 5000]))
        t1 = ts[i] - rng.randint(0, 1)          # a veces cae entre dos marcas
        t2 = ts[j]
        disco.reiniciar_contadores()
        regs = list(arbol.rango(t1, t2))
        esperado = [t for t in ts[max(0, i - 1):j + 1] if t1 <= t <= t2]
        k = len(esperado)
        assert [r[0] for r in regs] == esperado
        assert h - 1 + math.ceil(k / b) <= disco.lecturas <= h + math.ceil(k / b)
        assert disco.escrituras == 0
    assert list(arbol.rango(ts[-1] + 1, ts[-1] + 100)) == []


def test_insercion_tardia_y_formula(tmp_path):
    log, archivo, disco, arbol = _construir(tmp_path, 3000, llenado=0.7)
    ts = [r[0] for r in archivo.leer()]
    existentes = set(ts)
    rng = random.Random(3)
    insertados = 0
    while insertados < 400:
        t = rng.randint(ts[0], ts[-1])
        h = arbol.altura
        hojas, raiz = arbol.hojas, arbol.raiz
        disco.reiniciar_contadores()
        ok = arbol.insertar((t, 0.0, 0.0, 1.0, 0.0))
        assert ok == (t not in existentes)
        if not ok:
            continue
        existentes.add(t)
        insertados += 1
        assert disco.lecturas == h
        divisiones = disco.escrituras - 1 - (arbol.raiz != raiz)
        assert divisiones % 2 == 0                       # 1 + 2s + [raíz]
        assert (arbol.hojas - hojas) == (1 if divisiones else 0)
    assert arbol.validar()
    assert arbol.contar_rango(ts[0], ts[-1]) == len(existentes)


def test_reabrir_y_limite_de_memoria(tmp_path):
    log, archivo, disco, arbol = _construir(tmp_path, 5000)
    arbol.guardar()
    otro = ArbolBMas(disco)
    assert otro.altura == arbol.altura and otro.n == 5000
    log2 = DiscoSimulado(str(tmp_path / "l2.bin"), 512)
    a2 = ArchivoTelemetria(log2)
    a2.escribir(telemetria(5000))
    with pytest.raises(MemoriaInsuficiente):
        ArbolBMas.carga_masiva(DiscoSimulado(str(tmp_path / "a2.bin"), 512), a2,
                               memoria_registros=2 * capacidad_hoja(512))
