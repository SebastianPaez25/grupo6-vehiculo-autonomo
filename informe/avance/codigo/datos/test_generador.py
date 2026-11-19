from datos import generador as g


def test_semilla_fija_reproducible():
    assert g.nube_puntos_2d(50) == g.nube_puntos_2d(50)
    assert g.tramos_sensado(100) == g.tramos_sensado(100)


def test_tamanos_y_rangos():
    pts = g.nube_puntos_2d(200, "agrupada")
    assert len(pts) == 200
    claves = g.claves_distintas(5000)
    assert len(set(claves)) == 5000
    tramos, largo = g.tramos_sensado(300)
    assert len(tramos) == 300 and all(0 <= a <= b <= largo for a, b in tramos)
    assert g.escena_urbana_3d(999).shape == (999, 3)
