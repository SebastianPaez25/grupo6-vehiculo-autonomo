# Proyecto Final Integrador – Análisis de Algoritmos (SIST0175)

**Grupo 6 · Percepción y navegación de un vehículo autónomo urbano**
Sebastián Páez Castañeda · Johan Sebastián Acuña · Santiago Felipe Fajardo
Docente: Juan David Rodríguez Martínez · Universidad Sergio Arboleda

Entrega final (sesión 4): **los seis componentes (C1 a C6)**, el informe técnico y las diapositivas. Se procesa una nube de puntos sintética y una cuadrícula de ocupación para
detectar obstáculos, planear maniobras y ubicar sensores.

## Entregables

| Entregable | Dónde está |
|---|---|
| Informe técnico en PDF (13 páginas de cuerpo + anexos) | [`informe/final/informe_final_grupo6.pdf`](informe/final/informe_final_grupo6.pdf) |
| Código de los seis componentes | carpetas `c1_…` a `c6_…` (tabla de abajo) |
| README reproducible | este archivo (instalación, comandos y semilla fija) |
| Pruebas | `test_*.py` dentro de cada componente; `python -m pytest -q` ejecuta las 44 |
| Diapositivas | [`informe/final/presentacion.pdf`](informe/final/presentacion.pdf) |
| Avance de la sesión 2 (C1 a C3) | [`informe/avance/avance_grupo6.pdf`](informe/avance/avance_grupo6.pdf) |

Secciones del informe: 1. Descripción del caso · 2. Arquitectura · 3. Análisis teórico por componente ·
4. Validación empírica (con la tabla de E/S predichas frente a contadas de C5) · 5. Discusión ·
6. Conclusiones y reparto del trabajo · Referencias · Anexos.

| Comp. | Pilar | Algoritmo | Uso en el caso | Carpeta |
|---|---|---|---|---|
| C1 | Fundamentos | Par de puntos más cercanos por divide y vencerás (2D) vs fuerza bruta Θ(n²) | Distancia mínima entre obstáculos | `c1_par_mas_cercano/` |
| C2 | Fundamentos | Tabla hash dinámica con duplicación (método contable) | Mapa de vóxeles; espacio Θ(N) vs Θ((L/r)³) | `c2_mapa_voxeles/` |
| C3 | Diseño | Voraz: cobertura mínima de un segmento con intervalos (prueba por intercambio) | Cubrir la trayectoria [0, L] con tramos de sensado | `c3_cobertura_intervalos/` |
| C4 | Diseño | Backtracking en cuadrícula de ocupación: sin poda, con poda (cota Manhattan) y BFS | Maniobra de parqueo o evasión | `c4_backtracking_cuadricula/` |
| C5 | Memoria secundaria | Árbol B+ sobre `DiscoSimulado`, con conteo de E/S | Telemetría indexada por marca de tiempo; consultas por rango | `c5_arbol_bmas_disco/` |
| C6 | Aproximación | 2-aproximación de cobertura de vértices (emparejamiento maximal) vs fuerza bruta | Sensores en intersecciones que cubran todas las calles | `c6_cobertura_vertices/` |

## Requisitos e instalación

Python 3.10+ (probado con 3.13).

```bash
pip install -r requirements.txt      # numpy, matplotlib, pytest
```

## Cómo ejecutar (desde la raíz del repositorio)

```bash
# 1. Pruebas unitarias: 44 pruebas, todas deben pasar (~4 s)
python -m pytest -q

# 2. Experimentos: CSV, JSON y gráficas en resultados/
python -m experimentos.ejecutar_todos --rapido    # versión corta (~1 min)
python -m experimentos.ejecutar_todos             # tamaños completos (~7 min)
python -m experimentos.exp_c5                     # o uno solo: exp_c1 ... exp_c6

# 3. Regenerar las cifras del informe a partir de resultados/
python informe/generar_valores.py

# 4. Muestras de datos en CSV (opcional)
python -m datos.generador
```

El informe y las diapositivas están en `informe/final/` (PDF y fuente LaTeX; compilan con XeLaTeX o
pdfLaTeX, por ejemplo en Overleaf subiendo la carpeta completa). El avance de la sesión 2 está en
`informe/avance/`.

## Estructura

```
datos/generador.py              generador con semilla fija (SEMILLA = 6) para los seis componentes
comun/ordenamiento.py           merge sort propio (el núcleo no usa sorted)
comun/medicion.py               protocolo 4.3: perf_counter, 5 repeticiones, mediana e IQR, pendiente log-log
comun/graficas.py               gráficas log-log con pendiente
c1_par_mas_cercano/             par_cercano.py + test_par_cercano.py
c2_mapa_voxeles/                tabla_hash.py, mapa_voxeles.py + test_tabla_hash.py
c3_cobertura_intervalos/        cobertura.py + test_cobertura.py
c4_backtracking_cuadricula/     backtracking.py + test_backtracking.py
c5_arbol_bmas_disco/            disco_simulado.py, arbol_bmas.py + test_arbol_bmas.py
c6_cobertura_vertices/          cobertura_vertices.py + test_cobertura_vertices.py
experimentos/                   exp_c1.py ... exp_c6.py, ejecutar_todos.py
resultados/                     salidas de los experimentos (CSV, JSON, PNG)
informe/final/                  informe técnico (PDF + .tex), diapositivas (PDF + .tex), figuras y valores
informe/avance/                 avance de la sesión 2 (PDF + .tex, con el código de C1 a C3 en anexo)
informe/generar_valores.py      pasa los números de resultados/ al informe (valores.tex y tablas)
notebooks/                      cuaderno de demostración (C1, C2 y C3)
```

## Disco simulado (C5)

`c5_arbol_bmas_disco/disco_simulado.py` guarda bloques de tamaño fijo en un archivo binario y cuenta
cada `leer_bloque(i)` y `escribir_bloque(i, datos)`. Ningún otro código abre ese archivo. El árbol solo
mantiene en memoria el camino actual (h + 2 bloques) y verifica que h + 2 ≤ M/B, con M = N/20
registros. Si el docente entrega una clase `DiscoSimulado` oficial con la misma interfaz, se puede
reemplazar este archivo sin cambiar el árbol.

## Resultados principales (tamaños completos)

| Hipótesis | Predicho | Medido |
|---|---|---|
| C1 D&V, pendiente del tiempo (2¹⁰–2¹⁴) | ≈1,11 (n log n) | 1,13–1,16 |
| C1 trabajo de combinación contado | ≈1,11 | 1,11 |
| C1 vecinos revisados en la franja | ≤ 7 | máximo 2 |
| C2 costo acumulado, n = 2²⁰ | C(n) ≤ 3n | 2 621 434 ≤ 3 145 728; banco mínimo 2 |
| C2 espacio vs L/r | tabla 2, rejilla 3 | 2,00 y 3,00 |
| C3 voraz = óptimo (fuerza bruta) | 100 % | 321/321; 1679/1679 infactibles detectadas |
| C4 nodos sin poda | exponencial | ×1,24 por celda; 50 606 (sin poda) vs 16 (con poda) en 7×7 |
| C4 BFS | pendiente 1 | 1,02 |
| C5 E/S de carga masiva y búsqueda puntual | fórmula exacta | iguales en los 6 tamaños (N = 10⁵ a 10⁶) |
| C5 consultas por rango | (h−1) + ⌈k/b⌉ a h + ⌈k/b⌉ | 300 de 300 dentro |
| C6 razón de aproximación | ≤ 2 | 400/400 grafos; media 1,88 (calles), máximo 2,00 |

## Reparto del trabajo

| Integrante | Componentes |
|---|---|
| Santiago Felipe Fajardo | C1 y C2 |
| Sebastián Páez Castañeda | C3 y C4 |
| Johan Sebastián Acuña | C5 y C6 |
| Todos | experimentos, informe y diapositivas |

## Reglas de integridad (sección 9 del enunciado)

- Los algoritmos de C1 a C6 están implementados por el equipo.
- El núcleo de ningún componente usa `sorted`, `heapq`, `networkx`, `scikit-learn` ni otras
  bibliotecas para resolver el problema: ordenamos con `comun/ordenamiento.merge_sort`, y la tabla
  hash, las colas, la búsqueda binaria y el árbol B+ son propios.
- `sorted`, `dict` y `set` aparecen solo en pruebas, experimentos y verificaciones, como referencia;
  NumPy solo para generar datos y ajustar pendientes.

## Declaración de uso de asistentes de IA

Se usó Claude (Anthropic) como asistente para proponer la estructura del repositorio, redactar
borradores del código, de las pruebas, del informe y de las diapositivas, y depurar. El equipo revisó y
ejecutó todo el código, verificó los resultados y es responsable de su contenido y de poder explicarlo
en la sustentación.
