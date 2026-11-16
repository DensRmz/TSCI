"""Entrada Streamlit: navegación común y componentes nativos adaptables."""
import streamlit as st

st.set_page_config(page_title="AF7 · Análisis de patrones de compra", page_icon="🛒", layout="wide")
st.sidebar.title("AF7 · Análisis de patrones de compra")
st.sidebar.caption("Minería de datos con Apriori y recomendaciones de productos")
pagina = st.navigation([
    st.Page("pages/1_Panel_de_analisis.py", title="Panel de análisis", icon="📊"),
    st.Page("pages/2_Reglas_de_asociacion.py", title="Reglas de asociación", icon="🔎"),
    st.Page("pages/3_Recomendaciones.py", title="Recomendaciones", icon="🛒"),
])
pagina.run()
