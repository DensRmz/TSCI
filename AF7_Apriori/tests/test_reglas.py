import pytest
from src.mining.apriori import apriori
from src.mining.reglas import generar_reglas
from src.services.analisis import Parametros


def test_metricas():
    canastas = list(map(frozenset, [("A","B"), ("A","B"), ("A",), ("C",)]))
    reglas = generar_reglas(apriori(canastas, .5), .5, 1)
    fila = reglas[reglas.antecedente == "A"].iloc[0]
    assert fila.soporte == .5
    assert fila.confianza == pytest.approx(2/3)
    assert fila.lift == pytest.approx(4/3)
    assert fila.leverage == .125
    assert fila.conviccion == pytest.approx(1.5)
    from mlxtend.frequent_patterns import association_rules
    frecuentes = apriori(canastas, .5)
    import pandas as pd
    referencia = association_rules(pd.DataFrame({"support": list(frecuentes.values()),
        "itemsets": list(frecuentes)}), num_itemsets=len(canastas), metric="confidence", min_threshold=.5)
    ab = referencia[referencia.antecedents == frozenset("A")].iloc[0]
    assert fila.soporte == ab.support
    assert fila.confianza == ab.confidence
    assert fila.lift == ab.lift


@pytest.mark.parametrize("kwargs", [{"min_soporte": 0}, {"min_confianza": 2},
                                   {"min_lift": 1}, {"max_tamano": 0}])
def test_parametros(kwargs):
    with pytest.raises(ValueError):
        Parametros(**kwargs).validar()
