"""Servicio compartido por Streamlit y consola."""
from __future__ import annotations
import argparse
import math
import time
from pathlib import Path
from dataclasses import dataclass, asdict
import pandas as pd
from src.data.canastas import cargar_datos
from src.data.limpieza import preparar_datos
from src.mining.apriori import apriori
from src.mining.reglas import generar_reglas, tabla_frecuentes
from src.mining.validacion import validar_con_mlxtend
from src.recommendations.recomendador import construir_indice, evaluar, ejemplos_recomendaciones
from src.utils.archivos import SALIDA, ROOT, carpeta_nueva, guardar_json, huella, leer_json


@dataclass(frozen=True)
class Parametros:
    min_soporte: float = 0.01
    min_confianza: float = 0.50
    min_lift: float = 1.0001
    max_tamano: int | None = None

    def validar(self):
        if not math.isfinite(self.min_soporte) or not 0 < self.min_soporte <= 1:
            raise ValueError("Soporte: debe ser mayor que 0 y menor o igual a 1.")
        if not math.isfinite(self.min_confianza) or not 0 <= self.min_confianza <= 1:
            raise ValueError("Confianza: debe estar entre 0 y 1.")
        if not math.isfinite(self.min_lift) or self.min_lift <= 1:
            raise ValueError("Lift: debe ser estrictamente superior a 1.")
        if self.max_tamano is not None and (type(self.max_tamano) is not int or self.max_tamano < 1):
            raise ValueError("Tamaño máximo: entero positivo o sin límite.")


def ejecutar_analisis(datos: Path, parametros=Parametros(), validar=False, progreso=None):
    parametros.validar()
    datos = Path(datos).resolve()
    avisar = progreso or (lambda texto: None)
    inicio = time.perf_counter()
    avisar("Cargando y comprobando las particiones…")
    nombres = ["entrenamiento_apriori.csv", "prueba_apriori.csv",
               "catalogo_productos.csv", "resumen_preparacion.json"]
    for nombre in nombres:
        if not (datos / nombre).is_file():
            raise FileNotFoundError(f"Falta {nombre} en la preparación seleccionada.")
    ent = pd.read_csv(datos / nombres[0], dtype=str)
    pru = pd.read_csv(datos / nombres[1], dtype=str)
    for tabla in (ent, pru):
        if tabla[["InvoiceNo", "StockCode", "InvoiceDate"]].isna().any().any():
            raise ValueError("La preparación contiene campos clave vacíos.")
        if tabla.duplicated(["InvoiceNo", "StockCode"]).any():
            raise ValueError("La preparación contiene pares factura-producto duplicados.")
    if set(ent.InvoiceNo) & set(pru.InvoiceNo):
        raise ValueError("Hay facturas compartidas entre entrenamiento y prueba.")
    if ent.empty or pru.empty:
        raise ValueError("Las particiones deben contener facturas.")
    if pd.to_datetime(ent.InvoiceDate).max() > pd.to_datetime(pru.InvoiceDate).min():
        raise ValueError("El corte de entrenamiento y prueba no es cronológico.")
    entrenamiento, prueba, catalogo = cargar_datos(datos, True)
    avisar("Buscando conjuntos frecuentes con Apriori propio…")
    frecuentes = apriori(entrenamiento, parametros.min_soporte, parametros.max_tamano)
    avisar("Generando reglas y evaluando recomendaciones…")
    reglas = generar_reglas(frecuentes, parametros.min_confianza, parametros.min_lift, catalogo)
    indice = construir_indice(reglas)
    tablas = {"conjuntos_frecuentes": tabla_frecuentes(frecuentes, catalogo),
              "reglas_asociacion": reglas, "evaluacion": evaluar(indice, entrenamiento, prueba),
              "ejemplos_recomendaciones": ejemplos_recomendaciones(prueba, indice, catalogo)}
    if tablas["ejemplos_recomendaciones"].empty:
        tablas["ejemplos_recomendaciones"] = pd.DataFrame(columns=["canasta", "producto_recomendado", "descripcion"])
    validacion = validar_con_mlxtend(entrenamiento, frecuentes, parametros.min_soporte,
                                     parametros.max_tamano) if validar else None
    if validacion is False:
        raise ValueError("No coincide con MLxtend; no se publica el análisis.")
    resumen = leer_json(datos / "resumen_preparacion.json")
    try:
        origen = datos.relative_to(ROOT).as_posix()
    except ValueError:
        origen = datos.name
    meta = {"parametros": asdict(parametros), "preparacion": origen,
            "resumen_preparacion": resumen, "fuentes_sha256": {n: huella(datos / n) for n in nombres},
            "entrenamiento": {"facturas": len(entrenamiento), "productos": len(set().union(*entrenamiento))},
            "prueba": {"facturas": len(prueba), "productos": len(set().union(*prueba))},
            "conjuntos_frecuentes": len(frecuentes), "reglas": len(reglas),
            "validacion_mlxtend": validacion, "duracion_segundos": round(time.perf_counter()-inicio, 3),
            "limites": {"candidatos_por_nivel": 1000000, "segundos_por_etapa": 120, "reglas": 200000},
            "algoritmo": "Apriori propio vertical, presencia binaria, entrenamiento cronológico 80%"}
    avisar("Guardando una nueva ejecución…")
    destino = carpeta_nueva(SALIDA / "analisis", "ejecucion")
    for nombre, tabla in tablas.items():
        tabla.to_csv(destino / (nombre + ".csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(list(catalogo.items()), columns=["StockCode", "Description"]).to_csv(
        destino / "catalogo_productos.csv", index=False, encoding="utf-8-sig")
    guardar_json(destino / "analisis.json", meta)
    return destino


def preparar_nueva(archivo=ROOT / "Datos" / "Online Retail.xlsx"):
    destino = carpeta_nueva(SALIDA / "preparaciones", "preparacion")
    preparar_datos(Path(archivo), destino)
    return destino


def main():
    parser = argparse.ArgumentParser(description="AF7: preparación y análisis sin sobrescribir")
    parser.add_argument("--datos", type=Path, default=SALIDA)
    parser.add_argument("--preparar", action="store_true")
    parser.add_argument("--min-soporte", type=float, default=0.01)
    parser.add_argument("--min-confianza", type=float, default=0.50)
    parser.add_argument("--min-lift", type=float, default=1.0001)
    parser.add_argument("--max-tamano", type=int)
    parser.add_argument("--validar-mlxtend", action="store_true")
    args = parser.parse_args()
    datos = preparar_nueva() if args.preparar else args.datos.resolve()
    print(ejecutar_analisis(datos, Parametros(args.min_soporte, args.min_confianza,
        args.min_lift, args.max_tamano), args.validar_mlxtend, print))


if __name__ == "__main__":
    main()
