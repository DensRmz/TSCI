"""Entrada compatible para preparar Online Retail."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.limpieza import cargar_datos, preparar_datos

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preparación de Online Retail")
    parser.add_argument("--entrada", type=Path, default=ROOT / "Datos" / "Online Retail.xlsx")
    parser.add_argument("--salida", type=Path, required=True, help="Carpeta nueva o vacía")
    args = parser.parse_args()
    preparar_datos(args.entrada, args.salida)
