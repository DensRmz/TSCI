from __future__ import annotations
import pandas as pd

def validar_con_mlxtend(entrenamiento: list[frozenset], frecuentes: dict[frozenset, float],
                        min_soporte: float, max_tamano: int | None) -> bool | None:
    """Compara nuestros conjuntos frecuentes con los de la librería MLxtend.

    El README del proyecto menciona MLxtend. Si coinciden, queda demostrado que
    la implementación propia es correcta. Devuelve True/False, o None si MLxtend
    no está instalado o falla.
    """
    try:
        from mlxtend.frequent_patterns import apriori as ml_apriori
        from mlxtend.preprocessing import TransactionEncoder
    except ImportError:
        print("Validación omitida: mlxtend no está instalado (pip install mlxtend)")
        return None
    try:
        codificador = TransactionEncoder()
        matriz = codificador.fit(list(map(list, entrenamiento))).transform(
            list(map(list, entrenamiento)), sparse=True)
        tabla = pd.DataFrame.sparse.from_spmatrix(matriz.astype(bool), columns=codificador.columns_).astype(
            pd.SparseDtype(bool, False))
        ml = ml_apriori(tabla, min_support=min_soporte, use_colnames=True, max_len=max_tamano)
        ajenos = {frozenset(c): s for c, s in zip(ml["itemsets"], ml["support"])}
    except Exception as error:  # la API de MLxtend cambia entre versiones
        print(f"Validación omitida: MLxtend falló ({error})")
        return None

    iguales = (ajenos.keys() == frecuentes.keys()
               and all(abs(ajenos[c] - frecuentes[c]) < 1e-9 for c in ajenos))
    print(f"Validación con MLxtend: {len(ajenos)} conjuntos frecuentes (MLxtend) vs "
          f"{len(frecuentes)} (propio) -> {'COINCIDEN' if iguales else 'NO COINCIDEN'}")
    return iguales

