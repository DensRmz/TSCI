"""Presentación compartida: formatos, contexto, caché y evidencia de reglas."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from src.utils.archivos import ROOT, SALIDA, leer_resultado, leer_json
from src.recommendations.recomendador import construir_indice, recomendar_detallado

ETIQUETAS = {
    "registros_con_campos_clave_faltantes": "Campos clave faltantes",
    "registros_cancelados": "Cancelaciones",
    "registros_con_cantidad_o_precio_invalidos": "Cantidad o precio inválidos",
    "registros_de_servicios_o_ajustes": "Servicios y ajustes",
    "registros_duplicados_exactos": "Registros duplicados",
    "descripcion_faltante_o_vacia": "Descripción faltante o vacía",
    "otros_campos_clave": "Otros campos clave faltantes",
    "cantidad_no_positiva_o_no_numerica": "Cantidad inválida",
    "precio_no_positivo_o_no_numerico_despues_de_cantidad": "Precio inválido (después de cantidad)",
}


def porcentaje(valor):
    return f"{valor * 100:.2f} %"


def bytes_csv(tabla):
    """Exporta los valores originales; el formato visual no modifica la fuente."""
    return tabla.to_csv(index=False).encode("utf-8-sig")


@st.cache_data(show_spinner=False, max_entries=8)
def cargar_resultado(ruta, version):
    meta, tablas = leer_resultado(Path(ruta))
    for campo in ("parametros", "resumen_preparacion", "entrenamiento", "prueba",
                  "conjuntos_frecuentes", "reglas"):
        if campo not in meta:
            raise ValueError(f"Falta información del análisis: {campo}.")
    requeridas = {
        "reglas_asociacion": {"antecedente", "consecuente", "antecedente_descripcion",
                              "consecuente_descripcion", "soporte", "confianza", "lift"},
        "conjuntos_frecuentes": {"conjunto", "descripcion", "tamano", "soporte"},
    }
    for nombre, columnas in requeridas.items():
        if not columnas <= set(tablas[nombre].columns):
            raise ValueError(f"La tabla {nombre} está ausente o incompleta.")
    campos = {
        "parametros": {"min_soporte", "min_confianza", "min_lift", "max_tamano"},
        "resumen_preparacion": {"registros_originales", "registros_finales", "facturas_validas", "productos_distintos"},
        "entrenamiento": {"facturas", "productos"},
        "prueba": {"facturas", "productos"},
    }
    for nombre, requeridos in campos.items():
        if not isinstance(meta[nombre], dict) or not requeridos <= set(meta[nombre]):
            raise ValueError(f"La información de {nombre} está ausente o incompleta.")
    if meta["reglas"] != len(tablas["reglas_asociacion"]) or meta["conjuntos_frecuentes"] != len(tablas["conjuntos_frecuentes"]):
        raise ValueError("Las cifras del resumen no coinciden con las tablas guardadas.")
    return meta, tablas


@st.cache_data(show_spinner=False, max_entries=8)
def cargar_catalogo(ruta, version):
    tabla = pd.read_csv(ruta, dtype=str, encoding="utf-8-sig")
    if not {"StockCode", "Description"} <= set(tabla) or tabla[["StockCode", "Description"]].isna().any().any():
        raise ValueError("El catálogo contiene columnas o nombres inválidos.")
    return dict(zip(tabla.StockCode, tabla.Description))


def etiqueta_analisis(ruta, meta):
    try:
        fecha = datetime.strptime(Path(ruta).name.split("_")[1], "%Y%m%dT%H%M%SZ")
        fecha = fecha.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/Mexico_City"))
        fecha = fecha.strftime("%d/%m/%Y · %H:%M:%S")
    except (ValueError, IndexError):
        fecha = "Fecha no disponible"
    p = meta["parametros"]
    return (f"Análisis del {fecha} · Soporte {porcentaje(p['min_soporte'])} · "
            f"Confianza {porcentaje(p['min_confianza'])} · {Path(ruta).name.rsplit('_', 1)[-1]}")


def selector_resultado(mostrar_selector=True, mostrar_parametros=True):
    """analisis_activo es la fuente de verdad; el selector es opcional en consultas."""
    rutas = sorted((SALIDA / "analisis").glob("*/analisis.json"), reverse=True)
    etiquetas, opciones = {}, []
    for archivo in rutas:
        try:
            ruta = str(archivo.parent)
            etiquetas[ruta] = etiqueta_analisis(ruta, leer_json(archivo))
            opciones.append(ruta)
        except (OSError, ValueError, KeyError, TypeError):
            st.warning(f"No se pudo interpretar una ejecución guardada: {archivo.parent.name}.")
    if not opciones:
        st.info("Todavía no hay un análisis completo disponible. Abre las opciones avanzadas del panel para ejecutarlo.")
        return None
    pendiente = st.session_state.pop("analisis_pendiente", None)
    preferida = pendiente or st.session_state.get("analisis_activo", opciones[0])
    if preferida not in opciones:
        preferida = opciones[0]
    if pendiente:
        st.session_state["selector_analisis"] = preferida
    if mostrar_selector:
        seleccion = st.selectbox("Análisis activo", opciones, index=opciones.index(preferida),
                                format_func=lambda p: etiquetas[p], key="selector_analisis",
                                placeholder="Selecciona un análisis")
    else:
        seleccion = preferida
    anterior = st.session_state.get("analisis_activo")
    if anterior and anterior != seleccion:
        st.session_state["canasta"] = []
        st.session_state.pop("sugerencias", None)
        st.session_state["aviso_canasta"] = True
        for clave in list(st.session_state):
            if clave.startswith(("reg_", "freq_", "busqueda_")):
                del st.session_state[clave]
        st.info("Cambiaste de análisis. Se reiniciaron la canasta y los filtros para utilizar los nuevos resultados.")
    st.session_state["analisis_activo"] = seleccion
    try:
        archivos = list(Path(seleccion).glob("*.csv")) + [Path(seleccion) / "analisis.json"]
        version = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in archivos)
        meta, tablas = cargar_resultado(seleccion, version)
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"No se puede consultar este análisis: {error}")
        return None
    p = meta["parametros"]
    if mostrar_selector and mostrar_parametros:
        st.caption(f"Parámetros aplicados · Soporte: {porcentaje(p['min_soporte'])} · "
                   f"Confianza: {porcentaje(p['min_confianza'])} · Lift mínimo: {p['min_lift']:g} · "
                   f"Tamaño máximo: {p['max_tamano'] if p['max_tamano'] is not None else 'sin límite'}")
    return Path(seleccion), meta, tablas


def exportar(tabla, nombre, etiqueta="Descargar CSV"):
    st.download_button(etiqueta, bytes_csv(tabla), file_name=nombre + ".csv",
                       mime="text/csv", key="csv_" + nombre)


def tabla_reglas(reglas):
    vista = reglas[["antecedente_descripcion", "consecuente_descripcion", "soporte", "confianza", "lift"]].copy()
    vista["soporte"] *= 100
    vista["confianza"] *= 100
    return vista.rename(columns={"antecedente_descripcion": "Antecedente",
        "consecuente_descripcion": "Consecuente", "soporte": "Soporte (%)",
        "confianza": "Confianza (%)", "lift": "Lift"})


def configuracion_metricas():
    return {"Soporte (%)": st.column_config.NumberColumn(format="%.2f %%"),
            "Confianza (%)": st.column_config.NumberColumn(format="%.2f %%"),
            "Lift": st.column_config.NumberColumn(format="%.3f")}


def productos(texto):
    for nombre in str(texto).split(" | "):
        st.write("• " + nombre)


def evidencia(regla):
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.markdown("**Si la canasta contiene**")
        productos(regla["antecedente_descripcion"])
    with derecha:
        st.markdown("**Productos asociados**")
        productos(regla["consecuente_descripcion"])
    st.write(f"Soporte: **{porcentaje(regla['soporte'])}** · "
             f"Confianza: **{porcentaje(regla['confianza'])}** · Lift: **{regla['lift']:.3f}**")
    st.write(f"Entre las canastas que contienen todos los productos antecedentes, aproximadamente "
             f"el {porcentaje(regla['confianza'])} también contiene todos los productos consecuentes.")
    st.caption(f"Códigos: {regla['antecedente']} → {regla['consecuente']}. "
               "Las métricas corresponden a la regla completa en entrenamiento; asociación no implica causalidad.")


@st.cache_data(show_spinner=False, max_entries=8)
def indice_y_ejemplos(reglas):
    indice = construir_indice(reglas)
    ejemplos, vistos = [], set()
    for fila in reglas.sort_values(["confianza", "lift", "antecedente", "consecuente"],
                                  ascending=[False, False, True, True]).to_dict("records"):
        canasta = tuple(sorted(fila["antecedente"].split(", ")))
        if canasta in vistos:
            continue
        vistos.add(canasta)
        if recomendar_detallado(canasta, indice, 1):
            ejemplos.append(canasta)
        if len(ejemplos) == 3:
            break
    return indice, ejemplos


def resumen_preparacion(carpeta):
    archivo = carpeta / "resumen_preparacion.json"
    return leer_json(archivo) if archivo.exists() else None


@st.cache_data(show_spinner=False, max_entries=64)
def sugerencias_para_canasta(canasta, indice):
    """Consulta hasta el máximo permitido por la vista y reutiliza al cambiar k."""
    return recomendar_detallado(canasta, indice, 20) if canasta else []


@st.cache_data(show_spinner=False, max_entries=8)
def estados_catalogo(codigos, indice):
    """Estado por producto solo, independiente de la canasta y del límite visual.

    El máximo cubre todos los consecuentes posibles para no truncar cantidades.
    La caché incluye códigos y reglas: otro análisis no reutiliza estados ajenos.
    """
    limite = max(1, len({c for _, consecuentes, _ in indice["reglas"] for c in consecuentes}))
    estados = {}
    for codigo in codigos:
        if codigo not in indice["item"]:
            cantidad = 0
            texto = "Sin reglas aplicables"
        else:
            cantidad = len(recomendar_detallado([codigo], indice, limite))
            texto = (f"{cantidad} recomendaciones disponibles" if cantidad
                     else "Requiere combinarse con otro artículo")
        estados[codigo] = {"cantidad": cantidad, "estado": texto}
    return estados


@st.cache_data(show_spinner=False, max_entries=8)
def ejemplos_verificados(indice, codigos_catalogo):
    """Tres casos por categoría, con objetivo visible incluso con máximo 1.

    Se priorizan antecedentes de dos artículos y se admiten hasta tres para
    mantener la demostración breve. Cada eliminación se verifica contra todas
    las sugerencias posibles, sin truncarlas al máximo visible.
    """
    catalogo = frozenset(codigos_catalogo)
    limite = max(1, len({c for _, cons, _ in indice["reglas"] for c in cons}))
    ordenadas = sorted(indice["reglas"], key=lambda r: (
        len(r[0]), -r[2]["confianza"], -r[2]["lift"], -r[2]["soporte"],
        tuple(sorted(r[0])), tuple(sorted(r[1]))))
    categorias = {"individuales": [], "combinaciones": []}
    vistos = set()
    for ant, _, _ in ordenadas:
        canasta = tuple(sorted(ant))
        if canasta in vistos or not ant <= catalogo or not 1 <= len(ant) <= 3:
            continue
        vistos.add(canasta)
        categoria = "individuales" if len(ant) == 1 else "combinaciones"
        if len(categorias[categoria]) >= 3:
            continue
        recomendaciones = recomendar_detallado(canasta, indice, limite)
        if not recomendaciones:
            continue
        # El primer resultado siempre se verá al cargar el ejemplo.
        objetivo = recomendaciones[0]
        if objetivo["StockCode"] not in catalogo:
            continue
        if categoria == "combinaciones":
            if frozenset(objetivo["antecedente"].split(", ")) != ant:
                continue
            if any(objetivo["StockCode"] in {r["StockCode"] for r in
                    recomendar_detallado(ant - {codigo}, indice, limite)} for codigo in canasta):
                continue
        categorias[categoria].append({"productos": canasta, "recomendacion": objetivo})
        if all(len(ejemplos) == 3 for ejemplos in categorias.values()):
            break
    return categorias
