"""Pruebas de interacción sobre resultados reales, sin ejecutar minería."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import io
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.utils.archivos import SALIDA, leer_resultado
from src.utils.interfaz import indice_y_ejemplos, tabla_reglas, bytes_csv, cargar_resultado, etiqueta_analisis
from src.recommendations.recomendador import recomendar_detallado

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def real():
    rutas = sorted((SALIDA / "analisis").glob("*/analisis.json"), reverse=True)
    if not rutas:
        pytest.skip("Requiere un análisis real guardado.")
    ruta = rutas[0].parent
    meta, tablas = leer_resultado(ruta)
    return ruta, meta, tablas


def nueva(pagina=None):
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    if pagina:
        app.switch_page(pagina).run()
        assert not app.exception
    return app


def boton(app, etiqueta):
    return next(b for b in app.button if b.label == etiqueta)


def test_paginas_y_contexto(real):
    app = nueva()
    meta = real[1]
    assert next(m for m in app.metric if m.label == "Registros originales").value == f"{meta['resumen_preparacion']['registros_originales']:,}"
    assert next(m for m in app.metric if m.label == "Reglas de asociación").value == f"{meta['reglas']:,}"
    for pagina in ("pages/2_Reglas_de_asociacion.py", "pages/3_Recomendaciones.py"):
        app.switch_page(pagina).run()
        assert not app.exception
        assert app.session_state["analisis_activo"] == str(real[0])


def test_consultar_no_ejecuta_mineria(real):
    with patch("src.services.analisis.ejecutar_analisis", side_effect=AssertionError("No debe entrenar")):
        app = nueva("pages/3_Recomendaciones.py")
        app.button(key="ejemplo_0").click().run()
        app.number_input(key="max_recs").set_value(2).run()
        app.switch_page("pages/1_Panel_de_analisis.py").run()
        assert not app.exception


def test_catalogo_completo_agregar_quitar_limpiar_y_sin_recs(real):
    app = nueva("pages/3_Recomendaciones.py")
    assert not any(b.label == "Obtener recomendaciones" for b in app.button)
    assert not any(s.key == "selector_analisis" for s in app.selectbox)
    assert not any("Parámetros aplicados" in c.value for c in app.caption)
    catalogo = pd.read_csv(real[0] / "catalogo_productos.csv", dtype=str)
    selector = app.selectbox(key="producto_catalogo")
    assert len(selector.options) == len(catalogo)
    indice, _ = indice_y_ejemplos(real[2]["reglas_asociacion"])
    codigo = next(c for c in catalogo.StockCode if c not in indice["item"])
    selector.set_value(codigo).run()
    assert app.session_state["canasta"] == [codigo]
    assert app.selectbox(key="producto_catalogo").value is None
    app.selectbox(key="producto_catalogo").set_value(codigo).run()
    assert app.session_state["canasta"] == [codigo]
    assert any("No se encontraron recomendaciones" in i.value for i in app.info)
    assert app.session_state["sugerencias"][3] == []
    app.button(key="quitar_" + codigo).click().run()
    assert app.session_state["canasta"] == []
    assert app.session_state["sugerencias"][3] == []
    assert any("Agrega productos a tu canasta" in i.value for i in app.info)
    assert not app.exception


def test_ejemplo_recs_actualizacion_y_navegacion(real):
    app = nueva("pages/3_Recomendaciones.py")
    indice, ejemplos = indice_y_ejemplos(real[2]["reglas_asociacion"])
    assert ejemplos == indice_y_ejemplos(real[2]["reglas_asociacion"])[1]
    from src.utils.interfaz import ejemplos_verificados
    catalogo = pd.read_csv(real[0] / "catalogo_productos.csv", dtype=str)
    casos = ejemplos_verificados(indice, tuple(sorted(catalogo.StockCode)))
    app.button(key="ejemplo_0").click().run()
    seleccion = casos["individuales"][0]["productos"]
    assert app.session_state["canasta"] == list(seleccion)
    assert not app.exception
    recs = app.session_state["sugerencias"][3]
    assert recs
    assert any(s.value == f"Productos recomendados · {len(recs)}" for s in app.subheader)
    assert {r["StockCode"] for r in recs}.isdisjoint(seleccion)
    assert recs == recomendar_detallado(seleccion, indice, 5)
    app.number_input(key="max_recs").set_value(1).run()
    assert len(app.session_state["sugerencias"][3]) == 1
    assert any(s.value == "Productos recomendados · 1" for s in app.subheader)
    assert any(e.label.startswith("Ver evidencia") for e in app.expander)
    # Agregar un producto ya recomendado actualiza las sugerencias, nunca lo repite.
    producto = app.session_state["sugerencias"][3][0]["StockCode"]
    app.selectbox(key="producto_catalogo").set_value(producto).run()
    assert producto not in {r["StockCode"] for r in app.session_state["sugerencias"][3]}
    esperada = app.session_state["canasta"][:]
    app.switch_page("pages/2_Reglas_de_asociacion.py").run()
    app.switch_page("pages/3_Recomendaciones.py").run()
    assert app.session_state["canasta"] == esperada
    assert not app.exception
    boton(app, "Limpiar canasta").click().run()
    assert app.session_state["canasta"] == []
    assert app.session_state["sugerencias"][3] == []


def test_filtros_reglas_y_restablecer(real):
    app = nueva("pages/2_Reglas_de_asociacion.py")
    app.text_input(key="reg_buscar").set_value("inexistente_AF7").run()
    assert any("No se encontraron reglas" in i.value for i in app.info)
    boton(app, "Restablecer filtros").click().run()
    assert app.text_input(key="reg_buscar").value == ""
    app.radio(key="reg_alcance").set_value("Antecedentes").run()
    codigo = real[2]["reglas_asociacion"].iloc[0].antecedente.split(", ")[0]
    app.text_input(key="reg_buscar").set_value(codigo).run()
    original = real[2]["reglas_asociacion"]
    esperado = original[original.antecedente.str.contains(codigo, regex=False)
                       | original.antecedente_descripcion.str.contains(codigo, case=False, regex=False)]
    assert len(app.dataframe[0].value) == len(esperado)
    app.number_input(key="reg_confianza").set_value(90.0).run()
    assert (app.dataframe[0].value["Confianza (%)"] >= 90).all()
    app.radio(key="reg_direccion").set_value("Menor a mayor").run()
    assert app.dataframe[0].value.Lift.is_monotonic_increasing
    assert not app.exception


def test_filtros_metricas_consecuentes_y_tamano(real):
    app = nueva("pages/2_Reglas_de_asociacion.py")
    app.number_input(key="reg_soporte").set_value(1.5).run()
    app.number_input(key="reg_lift").set_value(5.0).run()
    app.selectbox(key="reg_tamano").set_value("Uno → uno").run()
    vista = app.dataframe[0].value
    origen = real[2]["reglas_asociacion"]
    esperado = origen[(origen.soporte >= .015) & (origen.lift >= 5)
        & ~origen.antecedente.str.contains(",", regex=False)
        & ~origen.consecuente.str.contains(",", regex=False)]
    assert len(vista) == len(esperado)
    boton(app, "Restablecer filtros").click().run()
    app.radio(key="reg_alcance").set_value("Consecuentes").run()
    codigo = origen.iloc[0].consecuente.split(", ")[0]
    app.text_input(key="reg_buscar").set_value(codigo).run()
    esperado = origen[origen.consecuente.str.contains(codigo, regex=False)
        | origen.consecuente_descripcion.str.contains(codigo, case=False, regex=False)]
    assert len(app.dataframe[0].value) == len(esperado)
    assert not app.exception


def test_seleccion_de_fila_y_metricas(real):
    # AppTest no expone eventos de selección de tablas: se simula únicamente
    # la respuesta del widget; se conserva su renderizado y la ejecución real de la página.
    import streamlit as st
    original = st.dataframe
    def seleccionar(*args, **kwargs):
        respuesta = original(*args, **kwargs)
        if kwargs.get("selection_mode") == "single-row":
            return SimpleNamespace(selection=SimpleNamespace(rows=[1]))
        return respuesta
    app = nueva("pages/2_Reglas_de_asociacion.py")
    with patch("streamlit.dataframe", side_effect=seleccionar):
        app.run()
    fila = real[2]["reglas_asociacion"].sort_values("lift", ascending=False, kind="stable").iloc[1]
    assert any(f"{fila.confianza * 100:.2f} %" in m.value
               and "Entre las canastas" in m.value for m in app.markdown)
    assert not app.exception


def test_cambio_analisis_reinicia_contexto(real):
    rutas = sorted((SALIDA / "analisis").glob("*/analisis.json"), reverse=True)
    if len(rutas) < 2:
        pytest.skip("Requiere dos análisis guardados.")
    app = nueva("pages/3_Recomendaciones.py")
    app.button(key="ejemplo_0").click().run()
    assert app.session_state["canasta"]
    app.switch_page("pages/1_Panel_de_analisis.py").run()
    app.selectbox(key="selector_analisis").set_value(str(rutas[1].parent)).run()
    assert app.session_state["analisis_activo"] == str(rutas[1].parent)
    assert app.session_state["canasta"] == []
    assert any("Cambiaste de análisis" in i.value for i in app.info)
    app.switch_page("pages/3_Recomendaciones.py").run()
    assert app.session_state["sugerencias"][3] == []
    assert app.session_state["sugerencias"][0] == str(rutas[1].parent)
    assert not any(s.key == "selector_analisis" for s in app.selectbox)
    assert any("canasta se reinició" in i.value for i in app.info)
    assert not app.exception


def test_conjuntos_filtros_y_porcentajes(real):
    app = nueva()
    app.selectbox(key="freq_tamano").set_value("Dos o más artículos").run()
    app.number_input(key="freq_soporte").set_value(2.0).run()
    vista = next(d.value for d in app.dataframe if "Artículos" in d.value.columns)
    assert (vista["Artículos"] >= 2).all()
    assert (vista["Soporte (%)"] >= 2).all()
    origen = real[2]["conjuntos_frecuentes"]
    assert len(vista) == min(25, len(origen[(origen.tamano >= 2) & (origen.soporte >= .02)]))
    assert not app.exception


def test_panel_orden_paginacion_y_detalle(real):
    app = nueva()
    titulos = [s.value for s in app.subheader]
    esperado = ["Datos de Online Retail · conjunto completo", "Cómo se limpiaron los registros",
                "Resultados de Apriori", "Explorar conjuntos frecuentes", "Evaluación de resultados",
                "Ejemplos reales de recomendaciones"]
    assert titulos == esperado
    originales = real[2]["conjuntos_frecuentes"].sort_values("soporte", ascending=False, kind="stable")
    vista = next(d.value for d in app.dataframe if "Artículos" in d.value.columns)
    assert len(vista) == 25
    assert list(vista["Soporte (%)"]) == list(originales.head(25).soporte * 100)
    app.selectbox(key="freq_limite").set_value(10).run()
    app.number_input(key="freq_pagina").set_value(2).run()
    vista = next(d.value for d in app.dataframe if "Artículos" in d.value.columns)
    assert list(vista["Soporte (%)"]) == list(originales.iloc[10:20].soporte * 100)
    app.selectbox(key="freq_orden").set_value("Menor soporte").run()
    vista = next(d.value for d in app.dataframe if "Artículos" in d.value.columns)
    assert vista["Soporte (%)"].is_monotonic_increasing
    app.selectbox(key="freq_tamano").set_value("1").run()
    vista = next(d.value for d in app.dataframe if "Artículos" in d.value.columns)
    assert (vista.Artículos == 1).all()
    assert any(e.label == "Consultar productos completos y códigos de un conjunto" for e in app.expander)
    assert not app.exception


def test_agregar_antecedentes_y_eliminar_actualiza_automaticamente(real):
    app = nueva("pages/3_Recomendaciones.py")
    indice, ejemplos = indice_y_ejemplos(real[2]["reglas_asociacion"])
    for codigo in ejemplos[0]:
        app.selectbox(key="producto_catalogo").set_value(codigo).run()
    assert app.session_state["sugerencias"][3] == recomendar_detallado(ejemplos[0], indice, 5)
    assert app.session_state["sugerencias"][3]
    codigo = ejemplos[0][0]
    app.button(key="quitar_" + codigo).click().run()
    actual = app.session_state["canasta"]
    assert codigo not in actual
    assert app.session_state["sugerencias"][3] == recomendar_detallado(actual, indice, 5)
    boton(app, "Limpiar canasta").click().run()
    assert app.session_state["sugerencias"][3] == []
    assert not any(e.label.startswith("Ver evidencia") for e in app.expander)
    assert not app.exception


def test_cache_sugerencias_no_recalcula_al_cambiar_maximo(real):
    from src.utils.interfaz import sugerencias_para_canasta
    indice, ejemplos = indice_y_ejemplos(real[2]["reglas_asociacion"])
    sugerencias_para_canasta.clear()
    with patch("src.utils.interfaz.recomendar_detallado", wraps=recomendar_detallado) as consulta:
        primera = sugerencias_para_canasta(tuple(sorted(ejemplos[0])), indice)[:1]
        segunda = sugerencias_para_canasta(tuple(sorted(ejemplos[0])), indice)[:10]
        assert consulta.call_count == 1
        assert primera == segunda[:1]


def test_descarga_conjuntos_no_se_limita_a_la_pagina(real):
    import streamlit as st
    original = st.download_button
    with patch("streamlit.download_button", wraps=original) as descargar:
        app = nueva()
    llamada = next(c for c in descargar.call_args_list if c.kwargs.get("key") == "csv_conjuntos_frecuentes")
    tabla = pd.read_csv(io.BytesIO(llamada.args[1]))
    esperado = real[2]["conjuntos_frecuentes"].sort_values("soporte", ascending=False, kind="stable")
    assert len(tabla) > 25
    pd.testing.assert_frame_equal(tabla, esperado.reset_index(drop=True))
    assert not app.exception


def test_formatos_exportacion_y_etiqueta(real):
    ruta, meta, tablas = real
    reglas = tablas["reglas_asociacion"]
    copia = reglas.copy(deep=True)
    vista = tabla_reglas(reglas)
    assert vista.iloc[0]["Confianza (%)"] == reglas.iloc[0].confianza * 100
    assert vista.iloc[0]["Soporte (%)"] == reglas.iloc[0].soporte * 100
    assert vista.iloc[0]["Lift"] == reglas.iloc[0].lift
    exportado = pd.read_csv(io.BytesIO(bytes_csv(reglas)))
    pd.testing.assert_frame_equal(exportado, copia)
    pd.testing.assert_frame_equal(reglas, copia)
    etiqueta = etiqueta_analisis(ruta, meta)
    assert f"{meta['parametros']['min_soporte']*100:.2f} %" in etiqueta


def test_sin_resultados(tmp_path, monkeypatch):
    from src.utils import interfaz
    monkeypatch.setattr(interfaz, "SALIDA", tmp_path)
    app = AppTest.from_string(
        "from src.utils.interfaz import selector_resultado\nselector_resultado()").run()
    assert not app.exception
    assert len(app.info) == 1


def test_resultado_incompleto(tmp_path):
    import json
    (tmp_path / "analisis.json").write_text(json.dumps({
        "parametros": {}, "resumen_preparacion": {}, "entrenamiento": {}, "prueba": {},
        "conjuntos_frecuentes": 1, "reglas": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="ausente o incompleta"):
        cargar_resultado(str(tmp_path), "prueba")
