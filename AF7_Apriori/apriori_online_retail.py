"""Sin argumentos abre la web; con argumentos ejecuta minería por consola.
Uso: python apriori_online_retail.py --datos salida_af7 --evaluar --graficas
El servicio siempre evalúa sobre prueba y guarda métricas y ejemplos.
"""
from pathlib import Path
import argparse
import subprocess
import sys


def iniciar_web():
    """Usa el entorno local si existe, sin exigir activarlo en la terminal."""
    raiz = Path(__file__).resolve().parent
    python_local = raiz / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    interprete = str(python_local) if python_local.is_file() else sys.executable
    comando = [interprete, "-m", "streamlit", "run", str(raiz / "app.py"),
               "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false"]
    print("Iniciando AF7. Espera la dirección que mostrará Streamlit cuando esté listo. Detener con Ctrl+C.", flush=True)
    try:
        return subprocess.call(comando, cwd=raiz)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__" and len(sys.argv) == 1:
    raise SystemExit(iniciar_web())

from src.data.canastas import cargar_datos, canastas_desde_tabla, dividir_transacciones
from src.mining.apriori import apriori
from src.mining.reglas import generar_reglas, tabla_frecuentes
from src.recommendations.recomendador import construir_indice, recomendar, evaluar, ejemplos_recomendaciones
from src.mining.validacion import validar_con_mlxtend
from src.utils.visualizacion import generar_graficas
from src.services.analisis import Parametros, ejecutar_analisis
from src.utils.archivos import SALIDA, leer_resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apriori propio sobre Online Retail")
    parser.add_argument("--datos", type=Path, default=SALIDA)
    parser.add_argument("--min-soporte", type=float, default=.01)
    parser.add_argument("--min-confianza", type=float, default=.5)
    parser.add_argument("--min-lift", type=float, default=1.0001)
    parser.add_argument("--max-tamano", type=int)
    parser.add_argument("--evaluar", action="store_true", help="La evaluación se incluye siempre")
    parser.add_argument("--graficas", action="store_true")
    parser.add_argument("--validar-mlxtend", action="store_true")
    args = parser.parse_args(argv)
    destino = ejecutar_analisis(args.datos, Parametros(args.min_soporte, args.min_confianza,
        args.min_lift, args.max_tamano), args.validar_mlxtend, print)
    if args.graficas:
        meta, tablas = leer_resultado(destino)
        _, _, catalogo = cargar_datos(args.datos, True)
        frecuentes = {frozenset(r.conjunto.split(", ")): r.soporte
                      for r in tablas["conjuntos_frecuentes"].itertuples()}
        generar_graficas(tablas["reglas_asociacion"], frecuentes, catalogo,
                         destino, tablas["evaluacion"])
    print(f"Resultados guardados en: {destino}")


if __name__ == "__main__":
    main()
