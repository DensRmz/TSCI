import pandas as pd
import pytest
from src.data.limpieza import limpiar_tabla, preparar_datos
from src.data.canastas import canastas_desde_tabla


def test_limpieza_y_canastas():
    def fila(inv="1", code="A", desc="Producto", cantidad=1, precio=1):
        return dict(InvoiceNo=inv, StockCode=code, Description=desc, Quantity=cantidad,
                    UnitPrice=precio, InvoiceDate="2011-01-01", CustomerID=None, Country="UK")
    df = pd.DataFrame([fila(), fila(), fila(code="X"), fila(inv="C2"),
                       fila(cantidad=0), fila(precio=-1), fila(desc="  "), fila(code="POST")])
    limpia, resumen = limpiar_tabla(df)
    assert len(limpia) == 2
    assert canastas_desde_tabla(limpia) == [frozenset(("A", "X"))]
    assert resumen["registros_cancelados"] == 1
    assert resumen["registros_con_cantidad_o_precio_invalidos"] == 2
    assert resumen["registros_con_campos_clave_faltantes"] == 1
    assert resumen["registros_de_servicios_o_ajustes"] == 1
    assert resumen["registros_duplicados_exactos"] == 1


def test_no_sobrescribe(tmp_path):
    (tmp_path / "existente.txt").touch()
    with pytest.raises(FileExistsError):
        preparar_datos(tmp_path / "no-existe.xlsx", tmp_path)
