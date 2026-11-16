"""Estados del catálogo: conteos sin truncamiento y contexto del análisis."""
from copy import deepcopy
import json
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.utils.archivos import ROOT, SALIDA, leer_resultado
from src.utils.interfaz import estados_catalogo
from src.recommendations.recomendador import construir_indice, recomendar_detallado


def test_tres_estados_consecuentes_multiples_y_duplicados():
    # Datos mínimos de prueba; nunca se guardan como resultados de Online Retail.
    filas = [{"antecedente": "A", "consecuente": f"P{i}", "confianza": .8,
              "lift": 2., "soporte": .1} for i in range(25)]
    filas += [{"antecedente": "A", "consecuente": "P0, P1", "confianza": .7, "lift": 2., "soporte": .1},
              {"antecedente": "B, C", "consecuente": "D", "confianza": .8, "lift": 2., "soporte": .1}]
    indice = construir_indice(pd.DataFrame(filas))
    estados = estados_catalogo(("A", "B", "C", "D", "N"), indice)
    assert estados["A"] == {"cantidad": 25, "estado": "25 recomendaciones disponibles"}
    assert estados["B"] == {"cantidad": 0, "estado": "Requiere combinarse con otro artículo"}
    assert estados["C"] == estados["B"]
    assert estados["D"] == {"cantidad": 0, "estado": "Sin reglas aplicables"}
    assert estados["N"] == estados["D"]
    assert len(recomendar_detallado(["A"], indice, 100)) == estados["A"]["cantidad"]


def test_sin_reglas():
    indice = construir_indice(pd.DataFrame(columns=["antecedente", "consecuente"]))
    assert estados_catalogo(("A",), indice)["A"]["estado"] == "Sin reglas aplicables"


@pytest.fixture
def real():
    rutas = sorted((SALIDA / "analisis").glob("*/analisis.json"), reverse=True)
    if not rutas:
        pytest.skip("Requiere un análisis real guardado")
    ruta = rutas[0].parent
    meta, tablas = leer_resultado(ruta)
    catalogo = pd.read_csv(ruta / "catalogo_productos.csv", dtype=str)
    return meta, tablas, catalogo


def test_todo_catalogo_real_coincide_con_recomendador(real):
    _, tablas, catalogo = real
    indice = construir_indice(tablas["reglas_asociacion"])
    estados = estados_catalogo(tuple(catalogo.StockCode), indice)
    for codigo in catalogo.StockCode:
        recomendaciones = recomendar_detallado([codigo], indice, len(catalogo))
        assert estados[codigo]["cantidad"] == len({r["StockCode"] for r in recomendaciones})
        esperado = (f"{len(recomendaciones)} recomendaciones disponibles" if recomendaciones else
                    "Requiere combinarse con otro artículo" if codigo in indice["item"] else
                    "Sin reglas aplicables")
        assert estados[codigo]["estado"] == esperado


def test_filtro_estados_y_cambio_de_analisis(real, tmp_path, monkeypatch):
    # Ejecuciones aisladas de prueba derivadas de reglas reales. No se escriben
    # archivos de salida_af7 ni se ejecuta minería para esta comprobación.
    from src.utils import interfaz
    meta, tablas, catalogo = real
    reglas = tablas["reglas_asociacion"]
    simples = reglas[~reglas.antecedente.str.contains(",", regex=False)]
    if simples.empty:
        pytest.skip("Se necesita un antecedente individual para probar el cambio")
    codigo = simples.iloc[0].antecedente
    nombre = catalogo.set_index("StockCode").loc[codigo, "Description"]
    otras = reglas[~reglas.antecedente.map(lambda valor: codigo in valor.split(", "))]
    for identificador, seleccion in [("ejecucion_20260102T120000Z_prueba", reglas),
                                     ("ejecucion_20260101T120000Z_prueba", otras)]:
        destino = tmp_path / "analisis" / identificador
        destino.mkdir(parents=True)
        copia = deepcopy(meta)
        copia["reglas"] = len(seleccion)
        (destino / "analisis.json").write_text(json.dumps(copia), encoding="utf-8")
        for clave, tabla in tablas.items():
            (seleccion if clave == "reglas_asociacion" else tabla).to_csv(
                destino / f"{clave}.csv", index=False, encoding="utf-8-sig")
        catalogo.to_csv(destino / "catalogo_productos.csv", index=False, encoding="utf-8-sig")
    monkeypatch.setattr(interfaz, "SALIDA", tmp_path)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.switch_page("pages/3_Recomendaciones.py").run()
    indice = construir_indice(reglas)
    estados = estados_catalogo(tuple(catalogo.StockCode), indice)
    cantidad = estados[codigo]["cantidad"]
    assert cantidad > 0
    opciones = app.selectbox(key="producto_catalogo").options
    assert len(opciones) == len(catalogo)
    assert any(nombre in o and f"{cantidad} recomendaciones disponibles" in o for o in opciones)
    app.radio(key="catalogo_filtro").set_value("Con recomendaciones directas").run()
    assert len(app.selectbox(key="producto_catalogo").options) == sum(
        e["cantidad"] > 0 for e in estados.values())
    app.selectbox(key="producto_catalogo").set_value(codigo).run()
    assert app.session_state["canasta"] == [codigo]
    # El estado individual no cambia al agregar un artículo ni al reducir k.
    app.number_input(key="max_recs").set_value(1).run()
    assert any(f"{cantidad} recomendaciones disponibles" in o and nombre in o
               for o in app.selectbox(key="producto_catalogo").options)
    app.switch_page("pages/1_Panel_de_analisis.py").run()
    otro = str(tmp_path / "analisis" / "ejecucion_20260101T120000Z_prueba")
    app.selectbox(key="selector_analisis").set_value(otro).run()
    app.switch_page("pages/3_Recomendaciones.py").run()
    app.radio(key="catalogo_filtro").set_value("Todos").run()
    opciones = app.selectbox(key="producto_catalogo").options
    assert any(nombre in o and "Sin reglas aplicables" in o for o in opciones)
    assert app.session_state["canasta"] == []
    assert app.session_state["sugerencias"][0] == otro
    assert not app.exception
