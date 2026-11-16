"""Recomendaciones explicables, con consecuentes simples o múltiples."""
import random
import pandas as pd


def construir_indice(reglas):
    entradas, por_item = [], {}
    for fila in reglas.to_dict("records"):
        ant = frozenset(fila["antecedente"].split(", "))
        cons = frozenset(fila["consecuente"].split(", "))
        posicion = len(entradas)
        entradas.append((ant, cons, fila))
        for codigo in ant:
            por_item.setdefault(codigo, []).append(posicion)
    return {"reglas": entradas, "item": por_item}


def recomendar_detallado(canasta, indice, k=5):
    if not isinstance(k, int) or k < 1:
        raise ValueError("El número de recomendaciones debe ser positivo.")
    canasta = frozenset(canasta)
    candidatas = set()
    for codigo in canasta:
        candidatas.update(indice["item"].get(codigo, []))
    mejores = {}
    for posicion in sorted(candidatas):
        ant, cons, regla = indice["reglas"][posicion]
        if not ant <= canasta:
            continue
        for codigo in sorted(cons - canasta):
            actual = mejores.get(codigo)
            puntaje = (regla["confianza"], regla["lift"], regla["soporte"])
            if actual is None or puntaje > actual[0]:
                mejores[codigo] = (puntaje, regla)
    orden = sorted(mejores, key=lambda c: (*(-v for v in mejores[c][0]), c))[:k]
    return [{"StockCode": c, **mejores[c][1]} for c in orden]


def recomendar(canasta, indice, k=5):
    return [(r["StockCode"], r["confianza"], r["lift"])
            for r in recomendar_detallado(canasta, indice, k)]


def ejemplos_recomendaciones(prueba, indice, catalogo, cantidad=8, k=3, semilla=42):
    elegibles = [c for c in prueba if 2 <= len(c) <= 8]
    random.Random(semilla).shuffle(elegibles)
    filas = []
    for canasta in elegibles:
        for r in recomendar_detallado(canasta, indice, k):
            filas.append({"canasta_codigos": ", ".join(sorted(canasta)),
                          "canasta": " | ".join(catalogo.get(c, c) for c in sorted(canasta)),
                          "producto_recomendado": r["StockCode"],
                          "descripcion": catalogo.get(r["StockCode"], r["StockCode"]), **r})
        if len(filas) >= cantidad:
            break
    return pd.DataFrame(filas[:cantidad])


def evaluar(indice: dict, entrenamiento: list[frozenset], prueba: list[frozenset],
            ks: tuple[int, ...] = (1, 3, 5, 10), semilla: int = 42) -> pd.DataFrame:
    """Mide la tasa de acierto (hit rate@k) con el método "ocultar uno".

    De cada canasta de prueba con 2+ productos se oculta uno al azar, se
    recomienda a partir de los demás y hay acierto si el oculto está entre los
    k recomendados.

    Compara dos métodos:
      - Método inicial: recomendar los k productos más vendidos en el
        entrenamiento que el cliente aún no tiene (no usa reglas).
      - Método Apriori: recomendar con las reglas de asociación.
    """
    azar = random.Random(semilla)
    kmax = max(ks)

    conteo: dict[str, int] = {}
    for c in entrenamiento:
        for it in c:
            conteo[it] = conteo.get(it, 0) + 1
    populares = [it for it, _ in sorted(conteo.items(), key=lambda x: (-x[1], x[0]))]

    total = con_recomendacion = 0
    aciertos_base = {k: 0 for k in ks}
    aciertos_apriori = {k: 0 for k in ks}
    for canasta in prueba:
        if len(canasta) < 2:
            continue
        oculto = azar.choice(sorted(canasta))
        visible = canasta - {oculto}
        total += 1

        base = [p for p in populares if p not in visible][:kmax]
        recs = [p for p, _, _ in recomendar(visible, indice, kmax)]
        con_recomendacion += bool(recs)
        for k in ks:
            aciertos_base[k] += oculto in base[:k]
            aciertos_apriori[k] += oculto in recs[:k]

    filas = [{
        "k": k,
        "canastas_evaluadas": total,
        "cobertura_apriori": con_recomendacion / total if total else 0.0,
        "acierto_metodo_inicial": aciertos_base[k] / total if total else 0.0,
        "acierto_apriori": aciertos_apriori[k] / total if total else 0.0,
    } for k in ks]
    res = pd.DataFrame(filas)
    res["mejora_veces"] = res["acierto_apriori"] / res["acierto_metodo_inicial"].where(
        res["acierto_metodo_inicial"] > 0)
    return res
