import streamlit as st
import pandas as pd

st.title("🛠️ Diagnóstico de Columnas CSV")

try:
    df_mun = pd.read_csv("MunicipiosJCyL_utf8.csv", encoding="utf-8-sig")
except Exception:
    df_mun = pd.read_csv("MunicipiosJCyL_utf8.csv", encoding="latin1")

try:
    df_hosp = pd.read_csv("Catalogo_Hospitales_Geolocalizados.csv", encoding="utf-8-sig")
except Exception:
    df_hosp = pd.read_csv("Catalogo_Hospitales_Geolocalizados.csv", encoding="latin1")

st.subheader("1. Columnas en MunicipiosJCyL_utf8.csv")
st.write(list(df_mun.columns))
st.dataframe(df_mun.head(2))

st.subheader("2. Columnas en Catalogo_Hospitales_Geolocalizados.csv")
st.write(list(df_hosp.columns))
st.dataframe(df_hosp.head(2))
