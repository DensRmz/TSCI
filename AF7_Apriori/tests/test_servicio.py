import pandas as pd
import pytest
from src.services import analisis
from src.utils.archivos import guardar_json, leer_resultado


def test_servicio_persistencia_y_no_sobrescritura(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    datos.mkdir()
    columnas = ["InvoiceNo", "InvoiceDate", "StockCode"]
    pd.DataFrame([("1","2011-01-01","A"), ("1","2011-01-01","B"),
                  ("2","2011-01-02","A"), ("2","2011-01-02","B"),
                  ("3","2011-01-03","C")], columns=columnas).to_csv(datos/"entrenamiento_apriori.csv",index=False)
    pd.DataFrame([("4","2011-02-01","A"), ("4","2011-02-01","B")],
                 columns=columnas).to_csv(datos/"prueba_apriori.csv",index=False)
    pd.DataFrame({"StockCode": ["A","B","C"], "Description": ["Uno","Dos","Tres"]}).to_csv(
        datos/"catalogo_productos.csv",index=False)
    guardar_json(datos/"resumen_preparacion.json", {"facturas_validas": 4})
    monkeypatch.setattr(analisis, "SALIDA", tmp_path/"salida")
    primera = analisis.ejecutar_analisis(datos, analisis.Parametros(.5, .5, 1.01))
    segunda = analisis.ejecutar_analisis(datos, analisis.Parametros(.5, .5, 1.01))
    assert primera != segunda
    meta, tablas = leer_resultado(primera)
    assert meta["reglas"] == len(tablas["reglas_asociacion"]) == 2
    assert meta["entrenamiento"]["facturas"] == 3
    assert (primera/"catalogo_productos.csv").is_file()
    sin_reglas = analisis.ejecutar_analisis(datos, analisis.Parametros(.5, 1, 100))
    meta_vacia, vacias = leer_resultado(sin_reglas)
    assert meta_vacia["reglas"] == 0
    assert vacias["reglas_asociacion"].empty
    assert vacias["ejemplos_recomendaciones"].empty
    df = pd.read_csv(datos/"prueba_apriori.csv", dtype=str)
    df["InvoiceNo"] = "1"
    df.to_csv(datos/"prueba_apriori.csv", index=False)
    with pytest.raises(ValueError, match="compartidas"):
        analisis.ejecutar_analisis(datos)


def test_fuente_ausente(tmp_path):
    with pytest.raises(FileNotFoundError, match="entrenamiento"):
        analisis.ejecutar_analisis(tmp_path)
