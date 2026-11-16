from __future__ import annotations
from itertools import combinations
import pandas as pd
import math
from time import monotonic
from src.mining.apriori import LimiteAnalisis

def _nombres(conjunto, catalogo: dict[str, str]) -> str:
    return " | ".join(catalogo.get(c, c) for c in sorted(conjunto))

def generar_reglas(frecuentes: dict[frozenset, float], min_confianza: float,
                   min_lift: float = 1.0,
                   catalogo: dict[str, str] | None = None, *,
                   max_reglas: int = 200000, max_segundos: float = 120) -> pd.DataFrame:
    """Genera reglas A -> B desde los conjuntos frecuentes.

    Para cada conjunto frecuente de tamaño >= 2 se prueban todas las divisiones
    en antecedente A y consecuente B. Por la propiedad Apriori, el soporte de A
    y de B ya fue calculado, así que no hay que volver a leer los datos.
    """
    if not math.isfinite(min_confianza) or not 0 <= min_confianza <= 1:
        raise ValueError("La confianza debe estar entre 0 y 1.")
    if not math.isfinite(min_lift) or min_lift <= 0:
        raise ValueError("El lift mínimo debe ser positivo y finito.")
    inicio = monotonic()
    catalogo = catalogo or {}
    filas = []
    for conjunto, sop_ab in frecuentes.items():
        if len(conjunto) < 2:
            continue
        for tam in range(1, len(conjunto)):
            for ant in combinations(conjunto, tam):
                if monotonic() - inicio > max_segundos or len(filas) >= max_reglas:
                    raise LimiteAnalisis("Límite de reglas o tiempo excedido; aumenta los umbrales.")
                a = frozenset(ant)
                b = conjunto - a
                sop_a, sop_b = frecuentes[a], frecuentes[b]
                confianza = sop_ab / sop_a
                lift = confianza / sop_b
                if confianza < min_confianza or lift < min_lift:
                    continue
                filas.append({
                    "antecedente": ", ".join(sorted(a)),
                    "consecuente": ", ".join(sorted(b)),
                    "antecedente_descripcion": _nombres(a, catalogo),
                    "consecuente_descripcion": _nombres(b, catalogo),
                    "soporte": sop_ab,
                    "confianza": confianza,
                    "lift": lift,
                    "leverage": sop_ab - sop_a * sop_b,
                    "conviccion": (1 - sop_b) / (1 - confianza) if confianza < 1 else float("inf"),
                })
    columnas = ["antecedente", "consecuente", "antecedente_descripcion",
                "consecuente_descripcion", "soporte", "confianza", "lift",
                "leverage", "conviccion"]
    reglas = pd.DataFrame(filas, columns=columnas)
    if not reglas.empty:
        # Los empates se resuelven por nombre para que cada ejecución dé el mismo orden
        reglas = reglas.sort_values(["lift", "confianza", "antecedente", "consecuente"],
                                    ascending=[False, False, True, True]).reset_index(drop=True)
    return reglas

def tabla_frecuentes(frecuentes: dict[frozenset, float],
                     catalogo: dict[str, str] | None = None) -> pd.DataFrame:
    catalogo = catalogo or {}
    filas = [{"conjunto": ", ".join(sorted(c)), "descripcion": _nombres(c, catalogo),
              "tamano": len(c), "soporte": s} for c, s in frecuentes.items()]
    df = pd.DataFrame(filas, columns=["conjunto", "descripcion", "tamano", "soporte"])
    return df.sort_values(["tamano", "soporte", "conjunto"],
                          ascending=[True, False, True]).reset_index(drop=True)

