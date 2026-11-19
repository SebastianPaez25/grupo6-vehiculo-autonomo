import pytest

from c2_mapa_voxeles.mapa_voxeles import celdas_rejilla_densa, construir_mapa, unidades_espacio_tabla
from c2_mapa_voxeles.tabla_hash import TablaHashVoxeles
from datos.generador import claves_distintas, claves_voxel, escena_urbana_3d


def test_insertar_y_obtener():
    t = TablaHashVoxeles()
    claves = claves_distintas(3000)
    for i, k in enumerate(claves):
        t.insertar(k, i)
    assert len(t) == 3000
    assert all(t.obtener(k) == i for i, k in enumerate(claves))
    assert t.obtener((10**6, 0, 0)) is None


def test_factor_de_carga_acotado():
    t = TablaHashVoxeles()
    for k in claves_distintas(10000):
        t.insertar(k)
        assert t.factor_carga() <= 0.75


def test_metodo_contable_banco_nunca_negativo():
    t = TablaHashVoxeles()
    for n, k in enumerate(claves_distintas(50000), start=1):
        t.insertar(k)
        assert t.banco >= 0
        assert t.costo_real_total <= 3 * n
    assert t.banco_minimo >= 0


def test_mapa_cuenta_puntos_por_voxel():
    pts = escena_urbana_3d(4000, semilla=3)
    mapa = construir_mapa(pts, r=0.5)
    referencia = {}
    for k in claves_voxel(pts, 0.5):
        referencia[k] = referencia.get(k, 0) + 1     # dict solo como referencia
    assert len(mapa) == len(referencia)
    assert dict(mapa.items()) == referencia
    assert sum(v for _, v in mapa.items()) == 4000


def test_espacio_tabla_vs_rejilla():
    mapa = construir_mapa(escena_urbana_3d(20000), r=0.25)
    assert unidades_espacio_tabla(mapa) < celdas_rejilla_densa(64.0, 0.25)


def test_capacidad_invalida():
    with pytest.raises(ValueError):
        TablaHashVoxeles(capacidad_inicial=6)
