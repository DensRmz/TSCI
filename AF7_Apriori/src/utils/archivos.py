"""Persistencia local sin sobrescritura y huellas de las fuentes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import uuid
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SALIDA = ROOT / "salida_af7"


def leer_json(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def guardar_json(ruta, contenido):
    with Path(ruta).open("x", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2, allow_nan=False)


def carpeta_nueva(base, prefijo):
    ruta = Path(base) / (prefijo + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                         + "_" + uuid.uuid4().hex[:8])
    ruta.mkdir(parents=True, exist_ok=False)
    return ruta


def huella(ruta):
    digest = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def leer_resultado(ruta):
    ruta = Path(ruta)
    meta = leer_json(ruta / "analisis.json")
    tablas = {}
    for nombre in ("conjuntos_frecuentes", "reglas_asociacion", "evaluacion", "ejemplos_recomendaciones"):
        archivo = ruta / (nombre + ".csv")
        tablas[nombre] = pd.read_csv(archivo, encoding="utf-8-sig",
            dtype={c: str for c in ("antecedente", "consecuente", "conjunto",
                   "producto_recomendado", "StockCode", "canasta_codigos")}) if archivo.exists() else pd.DataFrame()
    return meta, tablas
