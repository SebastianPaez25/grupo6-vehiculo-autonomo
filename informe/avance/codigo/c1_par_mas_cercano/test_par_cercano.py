import math
import random

import pytest

from c1_par_mas_cercano.par_cercano import Contador, fuerza_bruta, par_mas_cercano
from datos.generador import nube_puntos_2d


@pytest.mark.parametrize("dist", ["uniforme", "agrupada", "vertical"])
def test_coincide_con_fuerza_bruta(dist):
    for n in [2, 3, 4, 5, 17, 100, 513]:
        pts = nube_puntos_2d(n, dist, semilla=n)
        d1, _, _ = par_mas_cercano(pts)
        d2, _, _ = fuerza_bruta(pts)
        assert math.isclose(d1, d2, rel_tol=1e-12, abs_tol=1e-12)


def test_par_devuelto_tiene_esa_distancia():
    pts = nube_puntos_2d(300)
    d, p, q = par_mas_cercano(pts)
    assert math.isclose(math.dist(p, q), d)


def test_puntos_repetidos_y_colineales():
    assert par_mas_cercano([(1.0, 1.0), (5.0, 5.0), (1.0, 1.0)])[0] == 0.0
    linea = [(float(i), 0.0) for i in range(50)]
    random.Random(1).shuffle(linea)
    assert par_mas_cercano(linea)[0] == 1.0
    malla = [(float(i), float(j)) for i in range(10) for j in range(10)]
    assert par_mas_cercano(malla)[0] == 1.0


def test_franja_a_lo_sumo_7_vecinos():
    for dist in ["uniforme", "agrupada", "vertical"]:
        c = Contador()
        par_mas_cercano(nube_puntos_2d(4000, dist), c)
        assert c.max_por_punto_franja <= 7


def test_menos_de_dos_puntos():
    with pytest.raises(ValueError):
        par_mas_cercano([(0.0, 0.0)])
