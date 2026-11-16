from __future__ import annotations
from itertools import combinations
import math
from time import monotonic


class LimiteAnalisis(RuntimeError):
    """Se abortó el análisis completo, sin publicar resultados parciales."""

def apriori(canastas: list[frozenset], min_soporte: float,
            max_tamano: int | None = None, *, max_candidatos: int = 1000000,
            max_segundos: float = 120) -> dict[frozenset, float]:
    """Encuentra todos los conjuntos frecuentes (soporte >= min_soporte).

    Nivel 1: se cuenta cada producto y se conservan los frecuentes.
    Nivel k: JOIN  - se unen dos conjuntos de tamaño k-1 que comparten sus
                     primeros k-2 elementos (al estar ordenados, solo hay que
                     comparar vecinos con el mismo prefijo);
             PODA  - se descarta el candidato si algún subconjunto de tamaño
                     k-1 no es frecuente (propiedad Apriori);
             CONTEO- se calcula el soporte de los que sobreviven.
    Se detiene cuando ya no hay conjuntos frecuentes (o en max_tamano).

    Devuelve {frozenset(productos): soporte}.
    """
    if not math.isfinite(min_soporte) or not 0 < min_soporte <= 1:
        raise ValueError("El soporte debe ser mayor que 0 y menor o igual a 1.")
    if max_tamano is not None and (not isinstance(max_tamano, int) or max_tamano < 1):
        raise ValueError("El tamaño máximo debe ser un entero positivo o None.")
    inicio = monotonic()
    def comprobar():
        if monotonic() - inicio > max_segundos:
            raise LimiteAnalisis("Tiempo máximo excedido. Aumenta el soporte o limita el tamaño.")
    n = len(canastas)
    if n == 0:
        return {}

    # Bitset vertical: producto -> entero con un bit por transacción
    bits: dict[str, int] = {}
    for i, canasta in enumerate(canastas):
        comprobar()
        marca = 1 << i
        for item in canasta:
            bits[item] = bits.get(item, 0) | marca

    actual = {frozenset([it]): b for it, b in bits.items() if b.bit_count() / n >= min_soporte}
    frecuentes = {c: b.bit_count() / n for c, b in actual.items()}

    k = 2
    while actual and (max_tamano is None or k <= max_tamano):
        previos = sorted(tuple(sorted(c)) for c in actual)
        previos_set = set(actual)
        candidatos = set()

        for i in range(len(previos)):
            comprobar()
            for j in range(i + 1, len(previos)):
                a, b = previos[i], previos[j]
                if a[:-1] != b[:-1]:
                    break  # ordenados: ya no hay más con ese prefijo
                cand = frozenset(a) | {b[-1]}
                if all(frozenset(s) in previos_set for s in combinations(cand, k - 1)):
                    candidatos.add(cand)
                    if len(candidatos) > max_candidatos:
                        raise LimiteAnalisis("Demasiados candidatos. Aumenta el soporte o limita el tamaño.")

        siguiente = {}
        for cand in candidatos:
            comprobar()
            it = iter(cand)
            mascara = bits[next(it)]
            for e in it:
                mascara &= bits[e]
            if mascara.bit_count() / n >= min_soporte:
                siguiente[cand] = mascara

        frecuentes.update({c: m.bit_count() / n for c, m in siguiente.items()})
        actual = siguiente
        k += 1

    return frecuentes

