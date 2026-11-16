from __future__ import annotations
from pathlib import Path
from itertools import combinations
import random
import pandas as pd
from src.mining.reglas import _nombres

def _corto(texto: str, largo: int = 46) -> str:
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"

def _es_par(reglas: pd.DataFrame) -> pd.Series:
    """Marca las reglas de un solo producto a un solo producto (las más fáciles de leer)."""
    return (~reglas["antecedente"].str.contains(",", regex=False)
            & ~reglas["consecuente"].str.contains(",", regex=False))

def generar_graficas(reglas: pd.DataFrame, frecuentes: dict[frozenset, float],
                     catalogo: dict[str, str], carpeta: Path,
                     evaluacion: pd.DataFrame | None = None) -> list[str]:
    """Guarda gráficas listas para la presentación. Devuelve los nombres creados."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Aviso: matplotlib no está instalado; se omiten las gráficas (pip install matplotlib)")
        return []

    creadas = []
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    # a) Productos individuales más frecuentes
    unicos = sorted(((c, s) for c, s in frecuentes.items() if len(c) == 1),
                    key=lambda x: -x[1])[:15]
    if unicos:
        etiquetas = [_corto(_nombres(c, catalogo)) for c, _ in unicos][::-1]
        valores = [s for _, s in unicos][::-1]
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(etiquetas, valores, color="#2a6f97")
        ax.set_xlabel("Soporte (proporción de facturas que lo contienen)")
        ax.set_title("Los 15 productos más frecuentes en las canastas")
        fig.tight_layout()
        fig.savefig(carpeta / "grafica_productos_frecuentes.png", dpi=150)
        plt.close(fig)
        creadas.append("grafica_productos_frecuentes.png")

    if not reglas.empty:
        # b) Soporte vs confianza, color = lift
        fig, ax = plt.subplots(figsize=(8, 6))
        puntos = ax.scatter(reglas["soporte"], reglas["confianza"], c=reglas["lift"],
                            cmap="viridis", s=18, alpha=0.8)
        fig.colorbar(puntos, ax=ax, label="Lift")
        ax.set_xlabel("Soporte")
        ax.set_ylabel("Confianza")
        ax.set_title(f"Reglas de asociación ({len(reglas)} reglas)")
        fig.tight_layout()
        fig.savefig(carpeta / "grafica_reglas_soporte_confianza.png", dpi=150)
        plt.close(fig)
        creadas.append("grafica_reglas_soporte_confianza.png")

        # c) Las 12 reglas con mayor lift entre pares de productos (1 -> 1),
        #    sin repetir el mismo par en ambos sentidos
        vistas, filas = set(), []
        for r in reglas[_es_par(reglas)].itertuples():
            clave = frozenset(r.antecedente.split(", ") + r.consecuente.split(", "))
            if clave in vistas:
                continue
            vistas.add(clave)
            filas.append(r)
            if len(filas) == 12:
                break
        etiquetas = [_corto(f"{r.antecedente_descripcion} → {r.consecuente_descripcion}", 62)
                     for r in filas][::-1]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(etiquetas, [r.lift for r in filas][::-1], color="#c1121f")
        ax.axvline(1, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel("Lift (1 = sin asociación)")
        ax.set_title("Las reglas con mayor lift")
        fig.tight_layout()
        fig.savefig(carpeta / "grafica_reglas_top_lift.png", dpi=150)
        plt.close(fig)
        creadas.append("grafica_reglas_top_lift.png")

    # d) Comparación de métodos
    if evaluacion is not None and not evaluacion.empty:
        x = range(len(evaluacion))
        ancho = 0.38
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar([i - ancho / 2 for i in x], evaluacion["acierto_metodo_inicial"] * 100,
               ancho, label="Método inicial (más vendidos)", color="#9aa5b1")
        ax.bar([i + ancho / 2 for i in x], evaluacion["acierto_apriori"] * 100,
               ancho, label="Apriori (reglas)", color="#2a6f97")
        ax.set_xticks(list(x))
        ax.set_xticklabels([f"Top {k}" for k in evaluacion["k"]])
        ax.set_ylabel("Tasa de acierto (%)")
        ax.set_title("Comparación de métodos en las canastas de prueba")
        ax.legend()
        fig.tight_layout()
        fig.savefig(carpeta / "grafica_comparacion_metodos.png", dpi=150)
        plt.close(fig)
        creadas.append("grafica_comparacion_metodos.png")
    return creadas

