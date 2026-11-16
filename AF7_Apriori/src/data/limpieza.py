"""Carga y limpieza histórica de Online Retail, con exportación protegida."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


COLUMNAS = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]

CODIGOS_SERVICIO = {
    "POST", "DOT", "D", "M", "BANK CHARGES", "AMAZONFEE",
    "S", "CRUK", "C2", "PADS", "B",
}


def cargar_datos(archivo: Path) -> pd.DataFrame:
    if not archivo.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {archivo}")

    columnas_texto = {
        "InvoiceNo": "string",
        "StockCode": "string",
        "Description": "string",
        "Country": "string",
    }

    if archivo.suffix.lower() in {".xlsx", ".xls"}:
        datos = pd.read_excel(archivo, dtype=columnas_texto)
    elif archivo.suffix.lower() == ".csv":
        datos = pd.read_csv(archivo, dtype=columnas_texto, low_memory=False)
    else:
        raise ValueError("El archivo debe estar en formato XLSX, XLS o CSV.")

    faltantes = [col for col in COLUMNAS if col not in datos.columns]
    if faltantes:
        raise ValueError(f"No se encontraron estas columnas: {faltantes}")
    return datos[COLUMNAS].copy()


def limpiar_tabla(originales: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpieza histórica; las exclusiones son secuenciales y no se suman dos veces."""
    total_original = len(originales)

    datos = originales.copy()
    for columna in ("InvoiceNo", "StockCode", "Description"):
        datos[columna] = datos[columna].astype("string").str.strip()

    datos["InvoiceNo"] = datos["InvoiceNo"].str.upper()
    datos["StockCode"] = datos["StockCode"].str.upper()
    datos["Description"] = datos["Description"].str.replace(r"\s+", " ", regex=True)
    datos["Quantity"] = pd.to_numeric(datos["Quantity"], errors="coerce")
    datos["UnitPrice"] = pd.to_numeric(datos["UnitPrice"], errors="coerce")
    datos["InvoiceDate"] = pd.to_datetime(datos["InvoiceDate"], errors="coerce")

    nulos_clave = (
        datos["InvoiceNo"].isna()
        | datos["StockCode"].isna()
        | datos["Description"].isna()
        | datos["InvoiceDate"].isna()
        | datos["InvoiceNo"].eq("").fillna(True)
        | datos["StockCode"].eq("").fillna(True)
        | datos["Description"].eq("").fillna(True)
    )
    resumen = {
        "registros_originales": int(total_original),
        "registros_con_campos_clave_faltantes": int(nulos_clave.sum()),
    }
    descripciones_invalidas = datos["Description"].isna() | datos["Description"].eq("").fillna(True)
    resumen["detalle_exclusiones"] = {
        "descripcion_faltante_o_vacia": int(descripciones_invalidas.sum()),
        "otros_campos_clave": int((nulos_clave & ~descripciones_invalidas).sum()),
    }
    datos = datos.loc[~nulos_clave].copy()

    cancelaciones = datos["InvoiceNo"].str.startswith("C", na=False)
    resumen["registros_cancelados"] = int(cancelaciones.sum())
    datos = datos.loc[~cancelaciones].copy()

    valores_invalidos = (
        datos["Quantity"].le(0)
        | datos["UnitPrice"].le(0)
        | datos["Quantity"].isna()
        | datos["UnitPrice"].isna()
    )
    resumen["registros_con_cantidad_o_precio_invalidos"] = int(valores_invalidos.sum())
    cantidad_invalida = datos["Quantity"].le(0) | datos["Quantity"].isna()
    resumen["detalle_exclusiones"].update({
        "cantidad_no_positiva_o_no_numerica": int(cantidad_invalida.sum()),
        "precio_no_positivo_o_no_numerico_despues_de_cantidad": int((valores_invalidos & ~cantidad_invalida).sum()),
    })
    datos = datos.loc[~valores_invalidos].copy()

    servicios = datos["StockCode"].isin(CODIGOS_SERVICIO)
    resumen["registros_de_servicios_o_ajustes"] = int(servicios.sum())
    datos = datos.loc[~servicios].copy()

    resumen["registros_duplicados_exactos"] = int(datos.duplicated().sum())
    datos = datos.drop_duplicates().copy()

    if datos.empty:
        raise ValueError("No quedaron transacciones despues de la limpieza.")

    datos = datos.sort_values(["InvoiceDate", "InvoiceNo", "StockCode"])
    resumen["registros_finales"] = int(len(datos))
    resumen["detalle_descripciones"] = "Se excluyen nulas o vacías; variantes se conservan por StockCode."
    return datos, resumen


def preparar_datos(archivo: Path, carpeta_salida: Path) -> dict:
    """Escribe en una carpeta nueva o vacía; nunca reemplaza una preparación."""
    if carpeta_salida.exists() and any(carpeta_salida.iterdir()):
        raise FileExistsError("La carpeta de salida contiene archivos. Elige una carpeta nueva.")
    datos, resumen = limpiar_tabla(cargar_datos(archivo))
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    datos.to_csv(carpeta_salida / "transacciones_limpias.csv", index=False, encoding="utf-8-sig")

    catalogo = (
        datos.groupby(["StockCode", "Description"], as_index=False)
        .size()
        .sort_values(["StockCode", "size", "Description"], ascending=[True, False, True])
        .drop_duplicates(subset=["StockCode"], keep="first")
        .drop(columns=["size"])
        .sort_values("StockCode")
    )
    catalogo.to_csv(carpeta_salida / "catalogo_productos.csv", index=False, encoding="utf-8-sig")

    canastas_largo = (
        datos[["InvoiceNo", "InvoiceDate", "StockCode"]]
        .drop_duplicates(subset=["InvoiceNo", "StockCode"])
        .sort_values(["InvoiceDate", "InvoiceNo", "StockCode"])
        .reset_index(drop=True)
    )
    canastas_largo.to_csv(carpeta_salida / "canastas_apriori.csv", index=False, encoding="utf-8-sig")

    facturas = (
        canastas_largo.groupby("InvoiceNo", as_index=False)
        .agg(InvoiceDate=("InvoiceDate", "min"),
             n_productos=("StockCode", "size"),
             productos=("StockCode", lambda codigos: "|".join(sorted(codigos))))
        .sort_values(["InvoiceDate", "InvoiceNo"])
        .reset_index(drop=True)
    )
    facturas.to_csv(carpeta_salida / "canastas_por_factura.csv", index=False, encoding="utf-8-sig")

    corte = int(len(facturas) * 0.8)
    if corte == 0 or corte == len(facturas):
        raise ValueError("Se necesitan por lo menos dos facturas para separar los datos.")

    facturas_entrenamiento = set(facturas.iloc[:corte]["InvoiceNo"])
    entrenamiento = canastas_largo.loc[canastas_largo["InvoiceNo"].isin(facturas_entrenamiento)]
    prueba = canastas_largo.loc[~canastas_largo["InvoiceNo"].isin(facturas_entrenamiento)]
    entrenamiento.to_csv(carpeta_salida / "entrenamiento_apriori.csv", index=False, encoding="utf-8-sig")
    prueba.to_csv(carpeta_salida / "prueba_apriori.csv", index=False, encoding="utf-8-sig")

    resumen.update({
        "registros_finales": int(len(datos)),
        "productos_distintos": int(datos["StockCode"].nunique()),
        "facturas_validas": int(len(facturas)),
        "facturas_con_2_o_mas_productos": int(facturas["n_productos"].ge(2).sum()),
        "facturas_entrenamiento": int(corte),
        "facturas_prueba": int(len(facturas) - corte),
        "fecha_inicial": datos["InvoiceDate"].min().isoformat(),
        "fecha_final": datos["InvoiceDate"].max().isoformat(),
        "fuente": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "nota": "Apriori debe ajustarse solo con entrenamiento; prueba se reserva para evaluar.",
    })

    with (carpeta_salida / "resumen_preparacion.json").open("w", encoding="utf-8") as salida:
        json.dump(resumen, salida, ensure_ascii=False, indent=2)

    print("\nPREPARACION COMPLETADA")
    for clave, valor in resumen.items():
        print(f"{clave}: {valor}")
    print(f"\nArchivos guardados en: {carpeta_salida.resolve()}")
    return resumen



