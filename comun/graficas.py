"""Gráficas comunes: log-log con barras de dispersión (rango intercuartílico) y pendiente."""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from comun.medicion import pendiente_loglog  # noqa: E402

CARPETA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resultados")
COLORES = ["#2a6fb0", "#d1495b", "#3b9c5a", "#e0a030", "#7a5195"]

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 160, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "legend.frameon": False,
})


def loglog(series, titulo, archivo, xlabel="n", ylabel="tiempo (s)", referencias=(), n_min_ajuste=0):
    """series: lista de (etiqueta, filas_de_medir). Devuelve {etiqueta: pendiente}.

    La pendiente se ajusta solo con n >= n_min_ajuste (zona asintótica).
    """
    os.makedirs(CARPETA, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    pendientes = {}
    for k, (etq, filas) in enumerate(series):
        ns = np.array([f["n"] for f in filas], float)
        med = np.array([f["mediana"] for f in filas])
        q1 = np.array([f["q1"] for f in filas])
        q3 = np.array([f["q3"] for f in filas])
        sel = ns >= n_min_ajuste
        m, c = pendiente_loglog(ns[sel], med[sel])
        pendientes[etq] = m
        col = COLORES[k % len(COLORES)]
        ax.errorbar(ns, med, yerr=[med - q1, q3 - med], fmt="o", color=col, ms=4,
                    capsize=2, label=f"{etq}  (pendiente = {m:.2f})")
        ax.plot(ns[sel], np.exp(c) * ns[sel] ** m, "-", color=col, lw=1, alpha=0.7)
    for etq, xs, ys in referencias:
        ax.plot(xs, ys, "--", color="gray", lw=1, label=etq)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, archivo))
    plt.close(fig)
    return pendientes


def guardar(fig, archivo):
    os.makedirs(CARPETA, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, archivo))
    plt.close(fig)
