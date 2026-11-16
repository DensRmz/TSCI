import pandas as pd
from src.recommendations.recomendador import construir_indice, recomendar_detallado, recomendar


def test_antecedente_completo_y_consecuente_multiple():
    reglas = pd.DataFrame([{"antecedente": "A, B", "consecuente": "C, D",
                            "confianza": .8, "lift": 2., "soporte": .1}])
    indice = construir_indice(reglas)
    assert recomendar(["A"], indice) == []
    sugerencias = recomendar_detallado(["A", "B", "C"], indice)
    assert [r["StockCode"] for r in sugerencias] == ["D"]
    assert sugerencias[0]["antecedente"] == "A, B"
    assert recomendar(["A", "B", "C", "D"], indice) == []
