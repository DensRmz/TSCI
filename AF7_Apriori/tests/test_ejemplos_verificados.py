"""Ejemplos demostrables: ningún antecedente parcial mantiene el objetivo."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.utils.archivos import ROOT, SALIDA, leer_resultado
from src.utils.interfaz import ejemplos_verificados
from src.recommendations.recomendador import construir_indice, recomendar_detallado


def test_descarta_combinacion_con_regla_alternativa():
    # Reglas mínimas de prueba, nunca utilizadas como resultados de Online Retail.
    reglas = pd.DataFrame([
        {"antecedente": "A, B", "consecuente": "Z", "confianza": .9, "lift": 3., "soporte": .2},
        {"antecedente": "A", "consecuente": "Z", "confianza": .8, "lift": 2., "soporte": .2},
        {"antecedente": "C, D", "consecuente": "Y", "confianza": .8, "lift": 2., "soporte": .2},
    ])
    indice = construir_indice(reglas)
    casos = ejemplos_verificados(indice, tuple("ABCDYZ"))
    assert [e["productos"] for e in casos["combinaciones"]] == [("C", "D")]
    assert casos["combinaciones"][0]["recomendacion"]["StockCode"] == "Y"
    assert [e["productos"] for e in casos["individuales"]] == [("A",)]
    # Una nueva selección de reglas elimina la alternativa y habilita A+B.
    sin_alternativa = construir_indice(reglas.drop(index=1))
    nuevos = ejemplos_verificados(sin_alternativa, tuple("ABCDYZ"))
    assert ("A", "B") in [e["productos"] for e in nuevos["combinaciones"]]


def test_no_inventa_ejemplos_sin_reglas():
    indice = construir_indice(pd.DataFrame(columns=["antecedente", "consecuente"]))
    assert ejemplos_verificados(indice, ("A",)) == {"individuales": [], "combinaciones": []}


@pytest.fixture
def reales():
    rutas = sorted((SALIDA / "analisis").glob("*/analisis.json"), reverse=True)
    if not rutas:
        pytest.skip("Requiere resultados reales guardados.")
    ruta = rutas[0].parent
    _, tablas = leer_resultado(ruta)
    catalogo = pd.read_csv(ruta / "catalogo_productos.csv", dtype=str)
    indice = construir_indice(tablas["reglas_asociacion"])
    casos = ejemplos_verificados(indice, tuple(sorted(catalogo.StockCode)))
    return indice, casos, len(catalogo)


def test_seis_ejemplos_reales_y_todas_las_retiradas(reales):
    indice, casos, limite = reales
    assert len(casos["individuales"]) == len(casos["combinaciones"]) == 3
    assert len({e["productos"] for e in casos["individuales"]}) == 3
    assert len({e["productos"] for e in casos["combinaciones"]}) == 3
    assert casos == ejemplos_verificados(indice, tuple(sorted(
        pd.read_csv(sorted((SALIDA / "analisis").glob("*/catalogo_productos.csv"), reverse=True)[0],
                    dtype=str).StockCode)))
    for categoria, ejemplos in casos.items():
        for caso in ejemplos:
            canasta = caso["productos"]
            objetivo = caso["recomendacion"]["StockCode"]
            recs = recomendar_detallado(canasta, indice, limite)
            assert recs[0]["StockCode"] == objetivo
            assert objetivo not in canasta
            if categoria == "individuales":
                assert len(canasta) == 1
            else:
                assert 2 <= len(canasta) <= 3
                assert set(caso["recomendacion"]["antecedente"].split(", ")) == set(canasta)
                for codigo in canasta:
                    parciales = recomendar_detallado(set(canasta) - {codigo}, indice, limite)
                    assert objetivo not in {r["StockCode"] for r in parciales}


def test_tarjetas_cargan_y_retirar_actualiza_en_pantalla(reales):
    _, categorias, _ = reales
    casos = categorias["individuales"] + categorias["combinaciones"]
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.switch_page("pages/3_Recomendaciones.py").run()
    assert len([b for b in app.button if b.label == "Cargar ejemplo"]) == 6
    zona = next(n for n in app.get("flex_container") if "zona_canasta" in n.proto.id)
    assert zona.proto.height_config.pixel_height == 390
    app.number_input(key="max_recs").set_value(1).run()
    for i, caso in enumerate(casos):
        app.button(key=f"ejemplo_{i}").click().run()
        assert app.session_state["canasta"] == list(caso["productos"])
        assert app.session_state["sugerencias"][3][0]["StockCode"] == caso["recomendacion"]["StockCode"]
        if len(caso["productos"]) > 1:
            for codigo in caso["productos"]:
                app.button(key=f"ejemplo_{i}").click().run()
                app.button(key="quitar_" + codigo).click().run()
                assert caso["recomendacion"]["StockCode"] not in {
                    r["StockCode"] for r in app.session_state["sugerencias"][3]}
    assert not app.exception
