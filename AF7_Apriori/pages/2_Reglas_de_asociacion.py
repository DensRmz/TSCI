import streamlit as st
import plotly.express as px
from src.utils.interfaz import (selector_resultado, exportar, tabla_reglas,
                                configuracion_metricas, evidencia)

st.title("Reglas de asociación")
st.write("Una regla A → B describe con qué frecuencia aparece B entre las compras que contienen A. "
         "Una asociación no demuestra causalidad.")
resultado = selector_resultado()
if not resultado:
    st.stop()
reglas = resultado[2]["reglas_asociacion"]
if reglas.empty:
    st.info("Este análisis no generó reglas. Puedes revisar los parámetros en el panel.")
    st.stop()


def restablecer():
    for clave in list(st.session_state):
        if clave.startswith("reg_"):
            del st.session_state[clave]


buscar = st.text_input("Buscar producto por nombre o código", key="reg_buscar",
                       placeholder="Escribe parte del nombre o un código")
with st.expander("Filtros y ordenamiento"):
    alcance = st.radio("Buscar en", ["Ambos", "Antecedentes", "Consecuentes"], horizontal=True, key="reg_alcance")
    a, b, c = st.columns(3)
    sop = a.number_input("Soporte mínimo (%)", min_value=0.0, max_value=100.0, value=0.0, key="reg_soporte")
    conf = b.number_input("Confianza mínima (%)", min_value=0.0, max_value=100.0, value=0.0, key="reg_confianza")
    lift = c.number_input("Lift mínimo", min_value=0.0, value=1.0, key="reg_lift")
    a, b, c = st.columns(3)
    ordenar = a.selectbox("Ordenar por", ["Lift", "Confianza", "Soporte"], key="reg_orden")
    direccion = b.radio("Dirección", ["Mayor a menor", "Menor a mayor"], key="reg_direccion")
    cuantos = c.selectbox("Productos por regla", ["Todos", "Uno → uno", "Con varios productos"], key="reg_tamano")
st.button("Restablecer filtros", on_click=restablecer)
filtradas = reglas[(reglas.soporte >= sop/100) & (reglas.confianza >= conf/100) & (reglas.lift >= lift)]
if buscar.strip():
    columnas = (["antecedente", "antecedente_descripcion"] if alcance == "Antecedentes" else
                ["consecuente", "consecuente_descripcion"] if alcance == "Consecuentes" else
                ["antecedente", "consecuente", "antecedente_descripcion", "consecuente_descripcion"])
    mascara = filtradas[columnas].apply(
        lambda col: col.str.contains(buscar.strip(), case=False, regex=False, na=False)).any(axis=1)
    filtradas = filtradas[mascara]
pares = (~filtradas.antecedente.str.contains(",", regex=False)
         & ~filtradas.consecuente.str.contains(",", regex=False))
if cuantos != "Todos":
    filtradas = filtradas[pares if cuantos == "Uno → uno" else ~pares]
filtradas = filtradas.sort_values(ordenar.lower(), ascending=direccion == "Menor a mayor", kind="stable")
st.caption(f"{len(filtradas):,} de {len(reglas):,} reglas · Soporte y confianza en porcentaje; lift como factor.")
if filtradas.empty:
    st.info("No se encontraron reglas que cumplan con los filtros seleccionados. Usa «Restablecer filtros» para comenzar de nuevo.")
else:
    st.write("Selecciona una fila para consultar su interpretación y evidencia.")
    # La firma identifica el conjunto y orden de filas: una selección nunca apunta a otra regla tras filtrar.
    from hashlib import sha256
    firma = sha256((str(resultado[0]) + str(list(filtradas.index))).encode()).hexdigest()[:16]
    evento = st.dataframe(tabla_reglas(filtradas), hide_index=True, width="stretch", height=380,
        column_config=configuracion_metricas(), on_select="rerun", selection_mode="single-row",
        row_height=58, key="tabla_reglas_" + firma)
    filas = evento.selection.rows
    posicion = filas[0] if filas and filas[0] < len(filtradas) else 0
    if not filas:
        st.caption("Se muestra la primera regla como ejemplo; puedes seleccionar otra fila.")
    st.subheader("Interpretación de la regla")
    evidencia(filtradas.iloc[posicion])
    with st.expander("Gráfica de asociaciones"):
        st.write("Cada punto representa una regla. Pasa el cursor para consultar sus productos y métricas.")
        vista = tabla_reglas(filtradas)
        fig = px.scatter(vista, x="Soporte (%)", y="Confianza (%)", color="Lift",
                         hover_data=["Antecedente", "Consecuente"], title="Frecuencia y fuerza de las asociaciones")
        st.plotly_chart(fig, width="stretch")
st.caption("El CSV conserva los códigos, las métricas originales como proporciones y las columnas técnicas adicionales.")
exportar(filtradas, "reglas_asociacion", "Descargar reglas filtradas (CSV)")
