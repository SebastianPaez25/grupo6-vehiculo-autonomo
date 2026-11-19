"""Genera notebooks/avance_C1_C3.ipynb (demostración interactiva del avance).

    python notebooks/crear_notebook.py
    jupyter nbconvert --to notebook --execute --inplace notebooks/avance_C1_C3.ipynb
"""
import os

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

celdas = [
    md("# Proyecto Final Integrador – Grupo 6\n"
       "**Percepción y navegación de un vehículo autónomo urbano** · Demostración de C1, C2 y C3\n\n"
       "Sebastián Páez Castañeda · Johan Sebastián Acuña · Santiago Felipe Fajardo — "
       "Docente: Juan David Rodríguez Martínez\n\n"
       "Este cuaderno muestra cada componente con un ejemplo pequeño y resume los experimentos "
       "(que se generan con `python -m experimentos.ejecutar_todos`)."),
    code("import os, sys, json\n"
         "RAIZ = os.path.abspath('..') if os.path.basename(os.getcwd()) == 'notebooks' else os.getcwd()\n"
         "sys.path.insert(0, RAIZ)\n"
         "import matplotlib.pyplot as plt\n"
         "from IPython.display import Image, display\n"
         "from datos import generador as g\n"
         "RES = os.path.join(RAIZ, 'resultados')"),
    md("## C1 · Par de puntos más cercanos (divide y vencerás)\n"
       "$T(n) = 2T(n/2) + \\Theta(n)$ → Teorema Maestro caso 2 ($a=2$, $b=2$, $f(n)=\\Theta(n)=\\Theta(n^{\\log_2 2})$) → $\\Theta(n\\log n)$."),
    code("from c1_par_mas_cercano.par_cercano import par_mas_cercano, fuerza_bruta, Contador\n"
         "pts = g.nube_puntos_2d(2000, 'agrupada')\n"
         "c = Contador()\n"
         "d, p, q = par_mas_cercano(pts, c)\n"
         "print(f'D&V: d = {d:.6f} m entre {p} y {q}')\n"
         "print(f'Fuerza bruta: d = {fuerza_bruta(pts)[0]:.6f} m')\n"
         "print(f'distancias calculadas D&V = {c.distancias} vs fuerza bruta = {2000*1999//2}')\n"
         "print(f'máximo de vecinos revisados en la franja = {c.max_por_punto_franja} (cota teórica 7)')\n"
         "fig, ax = plt.subplots(figsize=(5, 5))\n"
         "ax.scatter(*zip(*pts), s=2, color='#9aa7b4')\n"
         "ax.scatter(*zip(p, q), s=40, color='#d1495b', label='par más cercano')\n"
         "ax.set_aspect('equal'); ax.legend(); ax.set_title('Obstáculos detectados (vista superior)'); plt.show()"),
    code("display(Image(os.path.join(RES, 'c1_loglog.png')))\n"
         "display(Image(os.path.join(RES, 'c1_operaciones.png')))"),
    md("## C2 · Mapa de vóxeles como tabla hash con duplicación\n"
       "Método contable: cada inserción nueva paga 3 créditos (1 para colocarse + 2 para el próximo rehash)."),
    code("from c2_mapa_voxeles.mapa_voxeles import construir_mapa, celdas_rejilla_densa\n"
         "escena = g.escena_urbana_3d(50000)\n"
         "mapa = construir_mapa(escena, r=0.5, instrumentar=True)\n"
         "print(f'puntos = {len(escena)}, vóxeles ocupados N = {len(mapa)}, capacidad m = {mapa.capacidad}, α = {mapa.factor_carga():.3f}')\n"
         "print(f'rejilla densa = {celdas_rejilla_densa(64, 0.5):,} celdas')\n"
         "print(f'costo real total = {mapa.costo_real_total} <= costo amortizado = {mapa.costo_amortizado_total}; banco mínimo = {mapa.banco_minimo}')\n"
         "xs = [k[0] for k, _ in mapa.items()]; ys = [k[1] for k, _ in mapa.items()]\n"
         "fig, ax = plt.subplots(figsize=(5, 5)); ax.scatter(xs, ys, s=1, color='#2a6fb0')\n"
         "ax.set_aspect('equal'); ax.set_title('Vóxeles ocupados (proyección en planta)'); plt.show()"),
    code("display(Image(os.path.join(RES, 'c2_metodo_contable.png')))\n"
         "display(Image(os.path.join(RES, 'c2_espacio.png')))"),
    md("## C3 · Voraz: cobertura mínima de la trayectoria [0, L]\n"
       "Regla: entre los tramos que empiezan dentro de lo ya cubierto, elegir el que llega más lejos."),
    code("from c3_cobertura_intervalos.cobertura import cobertura_minima, voraz_mas_largo\n"
         "ej = [(0, 5), (5, 10), (2, 8)]\n"
         "print('voraz (llega más lejos):', cobertura_minima(ej, 10))\n"
         "print('más largo primero      :', voraz_mas_largo(ej, 10), '<- contraejemplo, no es óptimo')\n"
         "tramos, L = g.tramos_sensado(40)\n"
         "sol = cobertura_minima(tramos, L)\n"
         "fig, ax = plt.subplots(figsize=(7, 4))\n"
         "for i, (a, b) in enumerate(tramos):\n"
         "    ax.plot([a, b], [i, i], color='#d1495b' if (a, b) in sol else '#c3ccd6', lw=3)\n"
         "ax.set_xlabel('posición sobre la trayectoria (m)'); ax.set_yticks([])\n"
         "ax.set_title(f'{len(sol)} tramos elegidos (rojo) de {len(tramos)}'); plt.show()"),
    code("display(Image(os.path.join(RES, 'c3_loglog.png')))\n"
         "print(json.dumps(json.load(open(os.path.join(RES, 'c3_resumen.json')))['optimalidad'], indent=1, ensure_ascii=False)[:600])"),
]

nb = nbf.v4.new_notebook(cells=celdas, metadata={"kernelspec": {
    "name": "python3", "display_name": "Python 3", "language": "python"}})
ruta = os.path.join(os.path.dirname(__file__), "avance_C1_C3.ipynb")
nbf.write(nb, ruta)
print("escrito", ruta)
