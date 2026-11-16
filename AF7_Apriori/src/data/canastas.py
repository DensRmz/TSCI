from __future__ import annotations
from pathlib import Path
import pandas as pd
PROPORCION_ENTRENAMIENTO = 0.8

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
    if not 0 < proporcion < 1:
        raise ValueError("La proporción debe estar entre 0 y 1.")
    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="raise")
    facturas = (df.groupby("InvoiceNo", as_index=False)["InvoiceDate"].min()
                .sort_values(["InvoiceDate", "InvoiceNo"]).reset_index(drop=True))
    corte = int(len(facturas) * proporcion)
    if corte == 0 or corte == len(facturas):
        raise ValueError("Se necesitan al menos dos facturas para separar las particiones.")
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

