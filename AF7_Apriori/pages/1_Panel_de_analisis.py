import pandas as pd
import plotly.express as px
import streamlit as st
from src.services.analisis import Parametros, ejecutar_analisis, preparar_nueva
from src.utils.archivos import SALIDA
from src.utils.interfaz import (selector_resultado, resumen_preparacion, exportar,
                                ETIQUETAS, porcentaje, productos, evidencia)

st.title("Panel de análisis")
st.write("Del registro de ventas a los patrones de compra: consulta los datos preparados, "
         "los conjuntos frecuentes y la evaluación de las recomendaciones.")
resultado = selector_resultado(mostrar_parametros=False)
meta, tablas = (resultado[1], resultado[2]) if resultado else (None, {})
try:
    resumen = meta["resumen_preparacion"] if meta else resumen_preparacion(SALIDA)
except (OSError, ValueError):
    resumen = None
if resumen:
    st.subheader("Datos de Online Retail · conjunto completo")
    fila1 = [("Registros originales", resumen["registros_originales"]),
             ("Registros válidos", resumen["registros_finales"]),
             ("Registros excluidos", resumen["registros_originales"] - resumen["registros_finales"])]
    for col, (titulo, valor) in zip(st.columns(3, border=True), fila1):
        col.metric(titulo, f"{valor:,}", help={
            "Registros originales": "Filas de ventas antes de aplicar la limpieza.",
            "Registros válidos": "Filas conservadas después de todos los criterios de limpieza.",
            "Registros excluidos": "Filas descartadas durante la limpieza, sin contarlas dos veces.",
            "Facturas / canastas": "Compras válidas agrupadas por factura, con presencia binaria de productos.",
            "Productos diferentes": "Códigos de producto distintos presentes en los registros válidos.",
        }[titulo])
    for col, (titulo, valor) in zip(st.columns(2, border=True),
        [("Facturas / canastas", resumen["facturas_validas"]), ("Productos diferentes", resumen["productos_distintos"])]):
        col.metric(titulo, f"{valor:,}", help="Compras agrupadas por factura, con presencia binaria de artículos."
                   if titulo == "Facturas / canastas" else "Códigos de producto distintos en los registros válidos.")

if resumen:
    st.subheader("Cómo se limpiaron los registros")
    criterios = {k: v for k, v in resumen.items() if k.startswith("registros_")
                 and k not in ("registros_originales", "registros_finales")}
    limpieza = pd.DataFrame({"Criterio": [ETIQUETAS.get(k, k.replace("_", " ").capitalize()) for k in criterios],
                            "Registros excluidos": list(criterios.values())})
    fig = px.bar(limpieza, x="Registros excluidos", y="Criterio", orientation="h",
                 text="Registros excluidos", color_discrete_sequence=["#137c83"],
                 title="Exclusiones por criterio")
    fig.update_layout(yaxis_title=None, margin=dict(l=15, r=30, t=50, b=20))
    st.plotly_chart(fig, width="stretch")
    st.caption("Las exclusiones son secuenciales: un registro se cuenta solo en el primer criterio aplicable.")
    with st.expander("Consultar desglose y descargar limpieza"):
        st.write("Campos clave: factura, código, descripción o fecha faltantes. Cancelaciones: "
                 "facturas cuyo identificador comienza con C. Cantidad/precio: valores no positivos "
                 "o no numéricos. Servicios/ajustes: códigos administrativos identificados. "
                 "Duplicados: filas exactamente repetidas.")
        st.dataframe(limpieza, hide_index=True, width="stretch")
        exportar(limpieza, "exclusiones")
        if "detalle_exclusiones" in resumen:
            st.write("Los siguientes valores desglosan grupos anteriores: no se suman de nuevo al total.")
            detalle = pd.DataFrame([(ETIQUETAS.get(k, k.replace("_", " ")), v)
                for k, v in resumen["detalle_exclusiones"].items()], columns=["Subcriterio", "Registros"])
            st.dataframe(detalle, hide_index=True, width="stretch")
            exportar(detalle, "detalle_exclusiones")


if resultado:
    st.subheader("Resultados de Apriori")
    p = meta["parametros"]
    st.caption(f"Parámetros aplicados · Soporte: {porcentaje(p['min_soporte'])} · "
               f"Confianza: {porcentaje(p['min_confianza'])} · Lift mínimo: {p['min_lift']:g} · "
               f"Tamaño máximo: {p['max_tamano'] if p['max_tamano'] is not None else 'sin límite'}")
    a, b = st.columns(2, border=True)
    a.metric("Conjuntos frecuentes", f"{meta['conjuntos_frecuentes']:,}")
    b.metric("Reglas de asociación", f"{meta['reglas']:,}")
    st.write(f"Después de limpiar los registros y construir canastas por factura, Apriori identificó estos patrones utilizando {meta['entrenamiento']['facturas']:,} "
             "canastas de entrenamiento. Cada producto cuenta por su presencia, no por la cantidad comprada.")
    st.caption(f"Duración registrada del análisis: {meta.get('duracion_segundos', 'no disponible')} segundos.")
    particiones = pd.DataFrame([{"Partición": n.capitalize(), "Canastas": meta[n]["facturas"],
        "Productos diferentes": meta[n]["productos"]} for n in ("entrenamiento", "prueba")])
    with st.expander("¿Qué datos se usaron para aprender y evaluar?"):
        st.dataframe(particiones, hide_index=True, width="stretch")
        st.write("El 80 % inicial de facturas se usa para aprender y el 20 % final para evaluar. "
                 "Soporte, confianza y lift se calculan exclusivamente con entrenamiento.")

    st.subheader("Explorar conjuntos frecuentes")
    st.write("Los conjuntos frecuentes son grupos de artículos que aparecen juntos en una cantidad "
             "significativa de compras. Usa los filtros para descubrir las combinaciones identificadas "
             "mediante Apriori. Son la base para construir reglas, no recomendaciones por sí mismos.")
    frecuentes = tablas["conjuntos_frecuentes"]
    a, b = st.columns(2)
    tamanos = ["Todos", "Dos o más artículos"] + [str(n) for n in sorted(frecuentes.tamano.unique())]
    tamano = a.selectbox("Cantidad de productos en el conjunto", tamanos, key="freq_tamano",
                        format_func=lambda n: f"{n} producto{'s' if n != '1' else ''}" if n.isdigit() else n)
    minimo = b.number_input("Soporte mínimo del conjunto (%)", min_value=0.0, max_value=100.0,
                            value=0.0, key="freq_soporte")
    a, b = st.columns(2)
    orden = a.selectbox("Orden de conjuntos", ["Mayor soporte", "Menor soporte"], key="freq_orden")
    limite = b.selectbox("Cantidad de resultados visibles", [10, 25, 50, 100], index=1, key="freq_limite")
    with st.expander("Búsqueda opcional por nombre o código"):
        buscar = st.text_input("Buscar dentro de los conjuntos", key="freq_buscar",
                               placeholder="Puedes explorar sin escribir nada")
    filtradas = frecuentes[frecuentes.soporte >= minimo / 100]
    if buscar.strip():
        filtradas = filtradas[filtradas.descripcion.str.contains(buscar.strip(), case=False, regex=False, na=False)
                              | filtradas.conjunto.str.contains(buscar.strip(), case=False, regex=False, na=False)]
    if tamano == "Dos o más artículos":
        filtradas = filtradas[filtradas.tamano >= 2]
    elif tamano != "Todos":
        filtradas = filtradas[filtradas.tamano == int(tamano)]
    filtradas = filtradas.sort_values("soporte", ascending=orden == "Menor soporte", kind="stable")
    st.caption(f"{len(filtradas):,} conjuntos cumplen los filtros. "
               "Soporte = porcentaje de canastas que contienen todos los artículos del conjunto.")
    if filtradas.empty:
        st.info("No hay conjuntos con estos filtros. Reduce el soporte o cambia el tamaño.")
    else:
        total_paginas = (len(filtradas) + limite - 1) // limite
        pagina = int(st.number_input("Página de conjuntos", min_value=1, max_value=total_paginas,
                                     value=1, key="freq_pagina"))
        visibles = filtradas.iloc[(pagina-1)*limite:pagina*limite]
        vista = visibles.rename(columns={"descripcion": "Productos del conjunto", "tamano": "Artículos",
                                          "soporte": "Soporte (%)"}).copy()
        vista["Productos del conjunto"] = vista["Productos del conjunto"].str.replace(" | ", "; ", regex=False)
        vista["Soporte (%)"] *= 100
        st.dataframe(vista[["Productos del conjunto", "Artículos", "Soporte (%)"]], hide_index=True,
            width="stretch", height=330, row_height=55,
            column_config={"Soporte (%)": st.column_config.NumberColumn(format="%.2f %%")})
        st.caption(f"Página {pagina} de {total_paginas} · {len(visibles)} resultados mostrados")
        with st.expander("Consultar productos completos y códigos de un conjunto"):
            seleccion_conjunto = st.selectbox("Conjunto de esta página", list(range(len(visibles))),
                format_func=lambda i: f"Conjunto {(pagina-1)*limite+i+1} · {porcentaje(visibles.iloc[i].soporte)}",
                key="freq_detalle")
            conjunto = visibles.iloc[seleccion_conjunto]
            productos(conjunto.descripcion)
            st.caption(f"Códigos: {conjunto.conjunto} · Artículos: {conjunto.tamano} · Soporte: {porcentaje(conjunto.soporte)}")
    st.caption("La descarga incluye todos los conjuntos filtrados, no solo la página visible.")
    exportar(filtradas, "conjuntos_frecuentes", "Descargar conjuntos filtrados (CSV)")

    st.subheader("Evaluación de resultados")
    st.write("Se oculta un producto por canasta y se comprueba si aparece entre las primeras k sugerencias. "
             "El método inicial recomienda productos populares de entrenamiento; Apriori utiliza reglas.")
    evaluacion = tablas["evaluacion"]
    if evaluacion.empty:
        st.info("Esta ejecución no contiene evaluación disponible.")
    else:
        ev = evaluacion.rename(columns={"k": "Máximo de sugerencias (k)", "canastas_evaluadas": "Canastas evaluadas",
            "cobertura_apriori": "Cobertura (%)", "acierto_metodo_inicial": "Acierto inicial (%)",
            "acierto_apriori": "Acierto de Apriori (%)", "mejora_veces": "Mejora frente al método inicial (veces)"}).copy()
        porcentajes = ["Cobertura (%)", "Acierto inicial (%)", "Acierto de Apriori (%)"]
        for col in porcentajes:
            ev[col] *= 100
        st.dataframe(ev, hide_index=True, width="stretch", column_config={
            **{c: st.column_config.NumberColumn(format="%.2f %%") for c in porcentajes},
            "Mejora frente al método inicial (veces)": st.column_config.NumberColumn(format="%.2f")})
        st.caption("k limita el número de sugerencias. Cobertura: canastas con alguna sugerencia. "
                   "Acierto: canastas donde se recuperó el producto oculto, entre todas las evaluadas. "
                   "No es exactitud de clasificación ni garantía de compra. Una mejora no calculable se muestra vacía.")
        exportar(evaluacion, "evaluacion")


if resultado:
    st.subheader("Ejemplos reales de recomendaciones")
    ejemplos = tablas["ejemplos_recomendaciones"]
    if ejemplos.empty:
        st.info("Esta ejecución no contiene ejemplos reales de recomendaciones.")
    else:
        posicion = st.selectbox("Consultar ejemplo real", list(range(len(ejemplos))),
                               format_func=lambda i: f"Ejemplo {i+1}")
        fila = ejemplos.iloc[posicion]
        a, b = st.columns(2)
        with a:
            st.markdown("**Productos presentes en la canasta**")
            productos(fila["canasta"])
        with b:
            st.markdown("**Producto sugerido**")
            st.write(fila.get("descripcion", fila.get("producto_recomendado", "Descripción no disponible")))
        if {"antecedente", "consecuente", "soporte", "confianza", "lift",
            "antecedente_descripcion", "consecuente_descripcion"} <= set(fila.index):
            with st.expander("Ver evidencia del ejemplo real"):
                evidencia(fila)
        exportar(ejemplos, "ejemplos_recomendaciones")

with st.expander("Opciones avanzadas · preparación y nuevo análisis"):
    st.write("Estos parámetros editables pertenecen a una nueva ejecución. No cambian los resultados del análisis activo.")
    st.caption("Cada operación guarda una carpeta nueva. Consultar recomendaciones no ejecuta Apriori.")
    if st.button("Preparar nuevamente desde Excel"):
        try:
            with st.status("Preparando Online Retail…") as estado:
                nueva = preparar_nueva()
                estado.update(label="Preparación completada", state="complete")
            st.session_state["preparacion_nueva"] = nueva
            st.success("Preparación completada y seleccionada para la próxima ejecución.")
        except Exception as error:
            st.error(f"No se pudo preparar: {error}")
    carpetas = ([SALIDA] if (SALIDA / "resumen_preparacion.json").exists() else [])
    carpetas += [p.parent for p in sorted((SALIDA / "preparaciones").glob("*/resumen_preparacion.json"), reverse=True)]
    if carpetas:
        preferida = st.session_state.get("preparacion_nueva", carpetas[0])
        fuente = st.selectbox("Preparación para el nuevo análisis", carpetas,
            index=carpetas.index(preferida) if preferida in carpetas else 0,
            format_func=lambda p: "Preparación original" if p == SALIDA else p.name)
        with st.form("parametros"):
            a, b, c = st.columns(3)
            soporte = a.number_input("Nuevo soporte (proporción 0–1)", value=0.01, format="%.4f")
            confianza = b.number_input("Nueva confianza (proporción 0–1)", value=0.50, format="%.4f")
            lift = c.number_input("Nuevo lift mínimo (> 1)", value=1.0001, format="%.4f")
            limitado = st.checkbox("Aplicar límite de artículos por conjunto")
            tamano = st.number_input("Límite de artículos (solo si marcas la casilla)", min_value=1, value=3, step=1)
            validar = st.checkbox("Validar conjuntos con MLxtend")
            st.caption("Sin la casilla de límite, el tamaño es ilimitado. Controles de minería: "
                       "un millón de candidatos por nivel, 200,000 reglas y 120 s por etapa. "
                       "Se aborta si se exceden; MLxtend puede consumir recursos adicionales.")
            iniciar = st.form_submit_button("Ejecutar nuevo análisis", type="primary")
        if iniciar:
            try:
                params = Parametros(soporte, confianza, lift, int(tamano) if limitado else None)
                params.validar()
                with st.status("Ejecutando nuevo análisis…", expanded=True) as estado:
                    destino = ejecutar_analisis(fuente, params, validar, st.write)
                    estado.update(label="Análisis completado", state="complete")
                st.session_state["analisis_pendiente"] = str(destino)
                st.rerun()
            except Exception as error:
                st.error(f"No se completó el análisis: {error}")
    else:
        st.warning("Falta una preparación completa. Prepara primero el archivo Excel.")
    if meta:
        with st.expander("Trazabilidad técnica del análisis activo"):
            st.json(meta)
