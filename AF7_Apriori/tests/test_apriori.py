from itertools import combinations
import random
import pytest
from src.mining.apriori import apriori, LimiteAnalisis
from src.mining.validacion import validar_con_mlxtend


def test_conocido_y_mlxtend():
    canastas = list(map(frozenset, [("A", "B"), ("A", "B"), ("A",), ("C",)]))
    resultado = apriori(canastas, 0.5)
    assert resultado == {frozenset("A"): .75, frozenset("B"): .5, frozenset(("A", "B")): .5}
    assert validar_con_mlxtend(canastas, resultado, .5, None) is True


def test_contra_conteo_exhaustivo():
    azar = random.Random(42)
    canastas = [frozenset(c for c in "ABCDE" if azar.random() < .65) for _ in range(40)]
    esperado = {}
    for k in range(1, 6):
        for candidato in combinations("ABCDE", k):
            soporte = sum(set(candidato) <= c for c in canastas) / len(canastas)
            if soporte >= .2:
                esperado[frozenset(candidato)] = soporte
    assert apriori(canastas, .2) == esperado
    assert all(len(c) <= 2 for c in apriori(canastas, .2, 2))


@pytest.mark.parametrize("soporte", [0, -1, 1.1, float("nan")])
def test_soporte_invalido(soporte):
    with pytest.raises(ValueError):
        apriori([], soporte)


def test_limites_y_vacio():
    assert apriori([], .5) == {}
    with pytest.raises(LimiteAnalisis):
        apriori([frozenset("ABC")], .1, max_candidatos=1)
    with pytest.raises(LimiteAnalisis):
        apriori([frozenset("A")], .1, max_segundos=-1)


def test_umbral_decimal_exacto():
    canastas = [frozenset("A")] * 7 + [frozenset("B")] * 93
    assert apriori(canastas, .07)[frozenset("A")] == .07
