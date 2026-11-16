"""Catálogo completo y sugerencias automáticas sobre reglas guardadas."""
from collections import Counter
import pandas as pd
import streamlit as st
from src.utils.archivos import ROOT
from src.utils.interfaz import (selector_resultado, cargar_catalogo, exportar, evidencia,
                                indice_y_ejemplos, sugerencias_para_canasta, estados_catalogo,
                                ejemplos_verificados)

st.title("Recomendaciones de productos")
st.write("Elige artículos del catálogo para descubrir productos relacionados. Las sugerencias se actualizan automáticamente.")
resultado = selector_resultado(mostrar_selector=False)
if not resultado:
    st.stop()
ruta, meta, tablas = resultado
st.caption("Sugerencias basadas en las asociaciones de Online Retail disponibles en el sistema.")
catalogo_path = ruta / "catalogo_productos.csv"
if not catalogo_path.exists():
    catalogo_path = ROOT / meta["preparacion"] / "catalogo_productos.csv"
try:
    catalogo = cargar_catalogo(str(catalogo_path), catalogo_path.stat().st_mtime_ns)
except (OSError, ValueError, KeyError) as error:
    st.error(f"No se pudo cargar el catálogo: {error}")
    st.stop()
if st.session_state.get("canasta_analisis") != str(ruta):
    st.session_state["canasta"] = []
    st.session_state.pop("sugerencias", None)
    st.session_state["canasta_analisis"] = str(ruta)
    st.session_state["producto_catalogo"] = None
if st.session_state.pop("aviso_canasta", False):
    st.info("Se actualizaron las asociaciones disponibles. La canasta se reinició para comenzar una nueva selección.")
st.session_state.setdefault("canasta", [])
indice, _ = indice_y_ejemplos(tablas["reglas_asociacion"])
categorias = ejemplos_verificados(indice, tuple(sorted(catalogo)))
ejemplos = categorias["individuales"] + categorias["combinaciones"]
estados = estados_catalogo(tuple(sorted(catalogo)), indice)


def seleccionar_producto():
    codigo = st.session_state.get("producto_catalogo")
    if codigo in catalogo and codigo not in st.session_state["canasta"]:
        st.session_state["canasta"] = [*st.session_state["canasta"], codigo]
    # No queda una selección pendiente ni hace falta pulsar Agregar.
    st.session_state["producto_catalogo"] = None


def quitar(codigo):
    st.session_state["canasta"] = [c for c in st.session_state["canasta"] if c != codigo]


def limpiar():
    st.session_state["canasta"] = []


def cargar_ejemplo(codigos):
    st.session_state["canasta"] = list(codigos)


izquierda, derecha = st.columns(2, gap="large")
with izquierda:
    st.subheader("Catálogo de productos")
    filtro = st.radio("Mostrar productos", ["Todos", "Con recomendaciones directas"],
                      horizontal=True, key="catalogo_filtro")
    nombres = Counter(catalogo.values())
    opciones = sorted((c for c in catalogo if filtro == "Todos" or estados[c]["cantidad"] > 0),
                      key=lambda c: (catalogo[c].casefold(), c))
    def etiqueta(codigo, catalogo=catalogo, nombres=nombres,
                 estados=estados,
                 seleccionados=frozenset(st.session_state["canasta"])):
        nombre = catalogo[codigo]
        if nombres[nombre] > 1:
            nombre += " · " + codigo
        nombre += " · " + estados[codigo]["estado"]
        if codigo in seleccionados:
            nombre += " · Ya está en la canasta"
        return nombre
    st.selectbox("Selecciona un producto para agregarlo", opciones, index=None,
                 key="producto_catalogo", placeholder="Abre el catálogo para elegir un artículo",
                 format_func=etiqueta, on_change=seleccionar_producto, disabled=not opciones)
    if not opciones:
        st.info("No hay productos con recomendaciones directas en este análisis. Selecciona «Todos» para explorar el catálogo.")
    st.caption(f"{len(opciones):,} de {len(catalogo):,} productos ordenados alfabéticamente. Puedes recorrer la lista "
               "o escribir dentro del selector para buscar. Elegir un artículo lo agrega inmediatamente.")
    k = int(st.number_input("Máximo de recomendaciones", min_value=1, max_value=20,
                           value=st.session_state.get("max_recs_guardado", 5), step=1, key="max_recs"))
    st.session_state["max_recs_guardado"] = k
with derecha:
    st.subheader(f"Tu canasta · {len(st.session_state['canasta'])} artículos")
    with st.container(height=390, border=True, key="zona_canasta"):
        if not st.session_state["canasta"]:
            st.caption("La canasta está vacía.")
        for inicio in range(0, len(st.session_state["canasta"]), 2):
            columnas = st.columns(2, gap="small")
            for columna, codigo in zip(columnas, st.session_state["canasta"][inicio:inicio+2]):
                with columna:
                    with st.container(height=165, border=True):
                        st.write(catalogo.get(codigo, codigo))
                        st.button("Eliminar", key="quitar_" + codigo, on_click=quitar,
                                  args=(codigo,), help="Código del producto: " + codigo)
    st.button("Limpiar canasta", on_click=limpiar, disabled=not st.session_state["canasta"])

with st.expander("Probar con una canasta de ejemplo"):
    st.write("Combinaciones construidas a partir de antecedentes de reglas del análisis utilizado. "
             "No representan necesariamente facturas históricas. Se verifican con el mismo recomendador.")
    numero = 0
    for categoria, titulo in [("individuales", "Recomendaciones individuales"),
                               ("combinaciones", "Recomendaciones por combinación")]:
        st.subheader(titulo)
        casos = categorias[categoria]
        if len(casos) < 3:
            st.info(f"Se encontraron {len(casos)} de 3 ejemplos válidos para esta categoría. "
                    "Las combinaciones se limitan a dos o tres artículos y deben superar la prueba de retirada.")
        for comienzo in range(0, len(casos), 3):
            columnas = st.columns(3)
            for columna, caso in zip(columnas, casos[comienzo:comienzo+3]):
                with columna:
                    with st.container(border=True):
                        st.markdown(f"**Ejemplo {numero+1}**")
                        for codigo in caso["productos"]:
                            st.write("• " + catalogo[codigo])
                        objetivo = caso["recomendacion"]["StockCode"]
                        st.write("Recomendación esperada: **" + catalogo[objetivo] + "**")
                        if categoria == "individuales":
                            st.caption("Este producto activa por sí solo una regla de recomendación.")
                        else:
                            st.caption("Retira cualquiera de estos artículos: la sugerencia esperada desaparecerá. "
                                       "Se verificó que ninguna otra regla la mantiene para la selección restante.")
                        st.button("Cargar ejemplo", key=f"ejemplo_{numero}", on_click=cargar_ejemplo,
                                  args=(caso["productos"],))
                numero += 1
seleccion = st.session_state["canasta"]
# La caché incluye la canasta y las reglas completas; cambiar k solo recorta la respuesta.
sugerencias = sugerencias_para_canasta(tuple(sorted(seleccion)), indice)[:k]
st.session_state["sugerencias"] = (str(ruta), tuple(seleccion), k, sugerencias)
st.subheader(f"Productos recomendados · {len(sugerencias)}")
if sugerencias:
    st.caption(f"{len(sugerencias)} productos mostrados para tu canasta actual · Máximo configurado: {k}.")
if not seleccion:
    st.info("Agrega productos a tu canasta para descubrir artículos relacionados.")
elif not sugerencias:
    st.info("No se encontraron recomendaciones para los artículos seleccionados. "
            "Puedes probar otras combinaciones o cargar una canasta de ejemplo.")
    if ejemplos:
        st.button("Usar la primera canasta de ejemplo", on_click=cargar_ejemplo, args=(ejemplos[0]["productos"],))
else:
    for r in sugerencias:
        with st.container(border=True):
            st.markdown("**" + catalogo.get(r["StockCode"], r["StockCode"]) + "**")
            st.write("Se sugiere por su asociación con: " + r["antecedente_descripcion"].replace(" | ", "; ") + ".")
            st.caption(f"Confianza de la regla: {r['confianza']:.2%}")
            with st.expander("Ver evidencia · " + catalogo.get(r["StockCode"], r["StockCode"])):
                evidencia(r)
    exportar(pd.DataFrame(sugerencias), "recomendaciones_canasta")
st.caption("Las sugerencias se actualizan al cambiar la canasta o el máximo, consultando solo reglas guardadas. "
           "Si varias reglas respaldan un artículo, se elige por confianza, lift y soporte, con desempate determinista. "
           "No se sugieren artículos que ya estén en tu canasta.")
