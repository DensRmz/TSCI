"""
Algoritmo Apriori y reglas de asociación sobre Online Retail (PIA AF7)
======================================================================
Técnica de minería de datos y algoritmo - 

Este programa continúa el trabajo de limpieza_datos.py. Toma las canastas de
compra ya preparadas y encuentra qué productos se compran juntos.

ENTRADAS (carpeta salida_af7, creada por limpieza_datos.py)
    entrenamiento_apriori.csv   InvoiceNo, InvoiceDate, StockCode  (80 % de las facturas)
    prueba_apriori.csv          InvoiceNo, InvoiceDate, StockCode  (20 % restante)
    catalogo_productos.csv      StockCode, Description
    transacciones_limpias.csv   (opcional) si faltan los archivos de arriba, el
                                programa reconstruye el mismo corte 80/20 desde él

SALIDAS (carpeta resultados_apriori dentro de salida_af7)
    conjuntos_frecuentes.csv    productos que se compran juntos con frecuencia
    reglas_asociacion.csv       reglas A -> B con soporte, confianza, lift,
                                leverage y convicción
    ejemplos_recomendaciones.csv  canastas de prueba y productos recomendados
    evaluacion.csv              acierto de Apriori vs. método inicial (--evaluar)
    grafica_*.png               gráficas para la presentación (--graficas)

FUNCIONAMIENTO, PASO A PASO
    1. Cargar    Cada factura es una canasta: el conjunto de StockCode comprados.
    2. Apriori   Búsqueda por niveles de conjuntos frecuentes (soporte >= mínimo).
                 Nivel k = unir conjuntos del nivel k-1, podar con la propiedad
                 Apriori (si un subconjunto no es frecuente, el conjunto tampoco)
                 y contar. Cada producto guarda un entero binario (bitset) con
                 las transacciones donde aparece; contar un candidato es un AND
                 entre bitsets, por eso corre en segundos con datos reales.
    3. Reglas    De cada conjunto frecuente se prueban todas las divisiones A -> B
                 y se conservan las que superan confianza y lift mínimos.
    4. Recomendar  Para una canasta se buscan las reglas cuyo antecedente está
                 contenido en ella y se sugieren los consecuentes que aún no tiene.
    5. Evaluar   Con las canastas de prueba (que Apriori nunca vio): se oculta un
                 producto, se recomienda con los demás y se revisa si se acertó.

MÉTRICAS (N = número de transacciones de entrenamiento)
    soporte(X)       = transacciones con X / N
    confianza(A->B)  = soporte(A U B) / soporte(A)
    lift(A->B)       = confianza(A->B) / soporte(B)          (> 1: asociación real)
    leverage(A->B)   = soporte(A U B) - soporte(A) * soporte(B)
    convicción(A->B) = (1 - soporte(B)) / (1 - confianza)    (inf si confianza = 1)

USO
    # Desde la carpeta del proyecto, igual que limpieza_datos.py:
    py ".\\AF7_Apriori\\Apriori\\apriori_online_retail.py" --datos ".\\AF7_Apriori\\salida_af7" --evaluar --graficas

    # Demostración con 10 compras de ejemplo (sin archivos):
    py apriori_online_retail.py

    # En Google Colab (después de subir el archivo del programa y los CSV):
    #   !python apriori_online_retail.py --datos salida_af7 --evaluar --graficas
    #   o bien:  from apriori_online_retail import main;  main(["--datos", "salida_af7"])
"""

from __future__ import annotations

import argparse
import random
import time
from itertools import combinations
from pathlib import Path

import pandas as pd

PROPORCION_ENTRENAMIENTO = 0.8  # igual que limpieza_datos.py


# ---------------------------------------------------------------------------
# 1. CARGA DE DATOS
# ---------------------------------------------------------------------------
def _leer_csv(archivo: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(archivo, dtype=str, encoding="utf-8-sig", **kwargs)


def canastas_desde_tabla(df: pd.DataFrame) -> list[frozenset]:
    """Convierte una tabla (InvoiceNo, StockCode) en una lista de canastas.

    Cada canasta es un conjunto de StockCode, así un producto no se cuenta dos
    veces en la misma factura.
    """
    return list(df.groupby("InvoiceNo")["StockCode"].apply(frozenset))


def catalogo_desde_transacciones(df: pd.DataFrame) -> dict[str, str]:
    """Descripción más frecuente de cada StockCode (algunos códigos tienen varias)."""
    conteo = (df.groupby(["StockCode", "Description"]).size().reset_index(name="n")
              .sort_values(["StockCode", "n"], ascending=[True, False])
              .drop_duplicates("StockCode"))
    return dict(zip(conteo["StockCode"], conteo["Description"]))


def dividir_transacciones(df: pd.DataFrame, proporcion: float = PROPORCION_ENTRENAMIENTO):
    """Reproduce el corte cronológico de limpieza_datos.py.

    Las facturas se ordenan por fecha y número; las primeras 80 % son de
    entrenamiento y el resto de prueba. Así Apriori nunca ve el futuro.
    """
    facturas = (df.groupby("InvoiceNo", as_index=False)["InvoiceDate"].min()
                .sort_values(["InvoiceDate", "InvoiceNo"]).reset_index(drop=True))
    corte = int(len(facturas) * proporcion)
    entrenamiento = set(facturas.iloc[:corte]["InvoiceNo"])
    unicos = df.drop_duplicates(["InvoiceNo", "StockCode"])
    return (unicos[unicos["InvoiceNo"].isin(entrenamiento)],
            unicos[~unicos["InvoiceNo"].isin(entrenamiento)])


def cargar_datos(carpeta: Path, necesita_prueba: bool):
    """Devuelve (canastas_entrenamiento, canastas_prueba, catalogo)."""
    f_ent = carpeta / "entrenamiento_apriori.csv"
    f_pru = carpeta / "prueba_apriori.csv"
    f_cat = carpeta / "catalogo_productos.csv"
    f_trx = carpeta / "transacciones_limpias.csv"

    if f_ent.exists():
        entrenamiento = canastas_desde_tabla(_leer_csv(f_ent, usecols=["InvoiceNo", "StockCode"]))
        prueba = []
        if necesita_prueba:
            if not f_pru.exists():
                raise FileNotFoundError(f"Falta {f_pru} (necesario para --evaluar)")
            prueba = canastas_desde_tabla(_leer_csv(f_pru, usecols=["InvoiceNo", "StockCode"]))
        if f_cat.exists():
            cat = _leer_csv(f_cat)
            catalogo = dict(zip(cat["StockCode"], cat["Description"]))
        else:
            catalogo = {}
        return entrenamiento, prueba, catalogo

    if f_trx.exists():
        print("Aviso: no están los archivos de canastas; se usa transacciones_limpias.csv\n")
        df = _leer_csv(f_trx, usecols=["InvoiceNo", "StockCode", "Description", "InvoiceDate"])
        ent, pru = dividir_transacciones(df)
        return canastas_desde_tabla(ent), canastas_desde_tabla(pru), catalogo_desde_transacciones(df)

    raise FileNotFoundError(
        f"No se encontraron entrenamiento_apriori.csv ni transacciones_limpias.csv en {carpeta}")


# ---------------------------------------------------------------------------
# 2. ALGORITMO APRIORI
# ---------------------------------------------------------------------------
def apriori(canastas: list[frozenset], min_soporte: float,
            max_tamano: int | None = None) -> dict[frozenset, float]:
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
    n = len(canastas)
    if n == 0:
        return {}
    min_conteo = min_soporte * n

    # Bitset vertical: producto -> entero con un bit por transacción
    bits: dict[str, int] = {}
    for i, canasta in enumerate(canastas):
        marca = 1 << i
        for item in canasta:
            bits[item] = bits.get(item, 0) | marca

    actual = {frozenset([it]): b for it, b in bits.items() if b.bit_count() >= min_conteo}
    frecuentes = {c: b.bit_count() / n for c, b in actual.items()}

    k = 2
    while actual and (max_tamano is None or k <= max_tamano):
        previos = sorted(tuple(sorted(c)) for c in actual)
        previos_set = set(actual)
        candidatos = set()

        for i in range(len(previos)):
            for j in range(i + 1, len(previos)):
                a, b = previos[i], previos[j]
                if a[:-1] != b[:-1]:
                    break  # ordenados: ya no hay más con ese prefijo
                cand = frozenset(a) | {b[-1]}
                if all(frozenset(s) in previos_set for s in combinations(cand, k - 1)):
                    candidatos.add(cand)

        siguiente = {}
        for cand in candidatos:
            it = iter(cand)
            mascara = bits[next(it)]
            for e in it:
                mascara &= bits[e]
            if mascara.bit_count() >= min_conteo:
                siguiente[cand] = mascara

        frecuentes.update({c: m.bit_count() / n for c, m in siguiente.items()})
        actual = siguiente
        k += 1

    return frecuentes


# ---------------------------------------------------------------------------
# 3. REGLAS DE ASOCIACIÓN
# ---------------------------------------------------------------------------
def _nombres(conjunto, catalogo: dict[str, str]) -> str:
    return " | ".join(catalogo.get(c, c) for c in sorted(conjunto))


def generar_reglas(frecuentes: dict[frozenset, float], min_confianza: float,
                   min_lift: float = 1.0,
                   catalogo: dict[str, str] | None = None) -> pd.DataFrame:
    """Genera reglas A -> B desde los conjuntos frecuentes.

    Para cada conjunto frecuente de tamaño >= 2 se prueban todas las divisiones
    en antecedente A y consecuente B. Por la propiedad Apriori, el soporte de A
    y de B ya fue calculado, así que no hay que volver a leer los datos.
    """
    catalogo = catalogo or {}
    filas = []
    for conjunto, sop_ab in frecuentes.items():
        if len(conjunto) < 2:
            continue
        for tam in range(1, len(conjunto)):
            for ant in combinations(conjunto, tam):
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


# ---------------------------------------------------------------------------
# 4. RECOMENDACIÓN
# ---------------------------------------------------------------------------
def construir_indice(reglas: pd.DataFrame) -> dict:
    """Prepara las reglas de consecuente único para recomendar rápido.

    Se indexan por cada producto del antecedente, así para una canasta solo se
    revisan las reglas que podrían aplicarse y no todas.
    """
    simples = reglas[~reglas["consecuente"].str.contains(",", regex=False)]
    antecedentes, consecuentes, puntajes, por_item = [], [], [], {}
    for i, r in enumerate(simples.itertuples()):
        ant = frozenset(r.antecedente.split(", "))
        antecedentes.append(ant)
        consecuentes.append(r.consecuente)
        puntajes.append((r.confianza, r.lift))
        for it in ant:
            por_item.setdefault(it, []).append(i)
    return {"ant": antecedentes, "cons": consecuentes, "punt": puntajes, "item": por_item}


def recomendar(canasta, indice: dict, k: int = 5) -> list[tuple[str, float, float]]:
    """Recomienda hasta k productos para una canasta.

    Devuelve [(StockCode, confianza, lift)] ordenados de mayor a menor confianza.
    Un producto solo se recomienda si no está ya en la canasta; si varias reglas
    apuntan al mismo producto se usa la de mayor confianza.
    """
    canasta = frozenset(canasta)
    candidatas = set()
    for it in canasta:
        candidatas.update(indice["item"].get(it, ()))
    mejor: dict[str, tuple[float, float]] = {}
    for i in candidatas:
        if not indice["ant"][i] <= canasta:
            continue
        cons = indice["cons"][i]
        if cons in canasta:
            continue
        if indice["punt"][i] > mejor.get(cons, (-1.0, -1.0)):
            mejor[cons] = indice["punt"][i]
    orden = sorted(mejor, key=lambda x: mejor[x], reverse=True)[:k]
    return [(p, mejor[p][0], mejor[p][1]) for p in orden]


def ejemplos_recomendaciones(prueba: list[frozenset], indice: dict, catalogo: dict[str, str],
                             cantidad: int = 8, k: int = 3, semilla: int = 42) -> pd.DataFrame:
    """Canastas reales de prueba con las recomendaciones que daría Apriori."""
    azar = random.Random(semilla)
    elegibles = [c for c in prueba if 2 <= len(c) <= 8]
    azar.shuffle(elegibles)
    filas = []
    for canasta in elegibles:
        recs = recomendar(canasta, indice, k)
        if not recs:
            continue
        filas.append({
            "canasta": " | ".join(catalogo.get(c, c) for c in sorted(canasta)),
            "recomendacion_1": catalogo.get(recs[0][0], recs[0][0]),
            "confianza_1": round(recs[0][1], 3),
            "lift_1": round(recs[0][2], 2),
            "todas_las_recomendaciones": " | ".join(catalogo.get(p, p) for p, _, _ in recs),
        })
        if len(filas) == cantidad:
            break
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 5. EVALUACIÓN CON LAS CANASTAS DE PRUEBA
# ---------------------------------------------------------------------------
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
    populares = [it for it, _ in sorted(conteo.items(), key=lambda x: -x[1])]

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


# ---------------------------------------------------------------------------
# 6. GRÁFICAS (requieren matplotlib)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 7. VALIDACIÓN CONTRA MLXTEND (opcional)
# ---------------------------------------------------------------------------
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
        tabla = pd.DataFrame.sparse.from_spmatrix(matriz, columns=codificador.columns_)
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


# ---------------------------------------------------------------------------
# 8. DEMOSTRACIÓN Y PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def datos_demo() -> list[frozenset]:
    """10 compras de ejemplo (se pueden verificar a mano)."""
    ejemplo = [
        {"PAN", "LECHE"}, {"PAN", "PANAL", "CERVEZA", "HUEVOS"},
        {"LECHE", "PANAL", "CERVEZA", "REFRESCO"}, {"PAN", "LECHE", "PANAL", "CERVEZA"},
        {"PAN", "LECHE", "PANAL", "REFRESCO"}, {"PAN", "LECHE"}, {"LECHE", "HUEVOS"},
        {"PAN", "PANAL", "CERVEZA"}, {"PAN", "LECHE", "HUEVOS"}, {"PANAL", "CERVEZA"},
    ]
    return [frozenset(c) for c in ejemplo]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Apriori y reglas de asociación (Online Retail)")
    ap.add_argument("--datos", help="Carpeta salida_af7 creada por limpieza_datos.py. "
                                    "Si se omite y existe ./salida_af7 se usa esa; si no, demo.")
    ap.add_argument("--min-soporte", type=float, default=None, help="Soporte mínimo (0-1), por defecto 0.01")
    ap.add_argument("--min-confianza", type=float, default=0.5, help="Confianza mínima (0-1)")
    ap.add_argument("--min-lift", type=float, default=1.0, help="Lift mínimo")
    ap.add_argument("--max-tamano", type=int, default=None,
                    help="Tamaño máximo de conjunto (útil si tarda demasiado)")
    ap.add_argument("--evaluar", action="store_true", help="Evalúa con prueba_apriori.csv")
    ap.add_argument("--graficas", action="store_true", help="Guarda gráficas PNG")
    ap.add_argument("--validar-mlxtend", action="store_true",
                    help="Compara los conjuntos frecuentes con MLxtend (si está instalado)")
    ap.add_argument("--salida", default=None,
                    help="Carpeta de salida (por defecto <datos>/resultados_apriori)")
    # parse_known_args: evita errores al ejecutarse dentro de Colab/Jupyter
    args, _ = ap.parse_known_args(argv)

    carpeta = Path(args.datos) if args.datos else (Path("salida_af7") if Path("salida_af7").is_dir() else None)

    catalogo: dict[str, str] = {}
    prueba: list[frozenset] = []
    if carpeta:
        entrenamiento, prueba, catalogo = cargar_datos(carpeta, args.evaluar)
        min_soporte = args.min_soporte if args.min_soporte is not None else 0.01
        salida = Path(args.salida) if args.salida else carpeta / "resultados_apriori"
    else:
        print(">>> Sin carpeta de datos: demostración con 10 compras de ejemplo\n")
        entrenamiento = datos_demo()
        min_soporte = args.min_soporte if args.min_soporte is not None else 0.3
        salida = Path(args.salida) if args.salida else Path("resultados_apriori")
    salida.mkdir(parents=True, exist_ok=True)

    productos = len(set().union(*entrenamiento)) if entrenamiento else 0
    tam_prom = sum(map(len, entrenamiento)) / len(entrenamiento)
    print(f"Canastas de entrenamiento: {len(entrenamiento)} | productos distintos: {productos} "
          f"| productos por canasta (promedio): {tam_prom:.1f}")
    print(f"Soporte mínimo: {min_soporte} | Confianza mínima: {args.min_confianza} "
          f"| Lift mínimo: {args.min_lift}\n")

    t0 = time.time()
    frecuentes = apriori(entrenamiento, min_soporte, args.max_tamano)
    t_frec = tabla_frecuentes(frecuentes, catalogo)
    por_tam = {int(k): int(v) for k, v in t_frec.groupby("tamano").size().items()}
    print(f"Conjuntos frecuentes: {len(t_frec)} (por tamaño: {por_tam}) [{time.time() - t0:.1f} s]")

    reglas = generar_reglas(frecuentes, args.min_confianza, args.min_lift, catalogo)
    print(f"Reglas de asociación: {len(reglas)}\n")
    if not reglas.empty:
        pares = reglas[_es_par(reglas)]
        vista = pares[["antecedente_descripcion", "consecuente_descripcion",
                       "soporte", "confianza", "lift"]].head(10).round(3)
        with pd.option_context("display.max_colwidth", 45, "display.width", 220):
            print("Las 10 reglas de un producto a un producto con mayor lift "
                  "(todas están en reglas_asociacion.csv):")
            print(vista.to_string(index=False))

    t_frec.to_csv(salida / "conjuntos_frecuentes.csv", index=False, encoding="utf-8-sig")
    reglas.to_csv(salida / "reglas_asociacion.csv", index=False, encoding="utf-8-sig")
    archivos = ["conjuntos_frecuentes.csv", "reglas_asociacion.csv"]

    indice = construir_indice(reglas)
    evaluacion = None
    if prueba and not reglas.empty:
        ejemplos = ejemplos_recomendaciones(prueba, indice, catalogo)
        if not ejemplos.empty:
            ejemplos.to_csv(salida / "ejemplos_recomendaciones.csv", index=False, encoding="utf-8-sig")
            archivos.append("ejemplos_recomendaciones.csv")
            print("\nEjemplo de recomendación con una canasta real de prueba:")
            fila = ejemplos.iloc[0]
            print(f"  Canasta:     {_corto(fila['canasta'], 150)}")
            print(f"  Recomienda:  {fila['todas_las_recomendaciones']}")

    if args.evaluar and prueba and not reglas.empty:
        evaluacion = evaluar(indice, entrenamiento, prueba)
        print(f"\nEVALUACIÓN con {int(evaluacion['canastas_evaluadas'].iloc[0])} canastas de prueba "
              f"(Apriori no las vio al aprender)")
        print(f"Cobertura (canastas con alguna recomendación): "
              f"{evaluacion['cobertura_apriori'].iloc[0]:.1%}")
        tabla = evaluacion[["k", "acierto_metodo_inicial", "acierto_apriori", "mejora_veces"]].copy()
        tabla["acierto_metodo_inicial"] = (tabla["acierto_metodo_inicial"] * 100).round(2).astype(str) + " %"
        tabla["acierto_apriori"] = (tabla["acierto_apriori"] * 100).round(2).astype(str) + " %"
        tabla["mejora_veces"] = tabla["mejora_veces"].round(1).astype(str) + "x"
        print(tabla.to_string(index=False))
        evaluacion.to_csv(salida / "evaluacion.csv", index=False, encoding="utf-8-sig")
        archivos.append("evaluacion.csv")

    if args.graficas:
        archivos += generar_graficas(reglas, frecuentes, catalogo, salida, evaluacion)

    if args.validar_mlxtend:
        print()
        validar_con_mlxtend(entrenamiento, frecuentes, min_soporte, args.max_tamano)

    print(f"\nArchivos guardados en {salida.resolve()}:")
    for a in archivos:
        print(f"  - {a}")


if __name__ == "__main__":
    main()
