import pandas as pd
import streamlit as st

from common import PATH_CALENDARIO, load_calendario

st.set_page_config(page_title="Calendário — Macro Dashboard", page_icon="🗓️", layout="wide")
st.title("🗓️ Calendário econômico")
st.caption("Próximas divulgações de inflação, emprego e decisões de juros — Brasil e EUA.")

if not PATH_CALENDARIO.exists():
    st.error("Sem dados. Rode `python scripts/fetch_calendario_brasil.py` e `python scripts/fetch_calendario_eua.py`.")
    st.stop()

cal = load_calendario()

with st.sidebar:
    st.subheader("Filtros")
    paises = st.multiselect("País", options=sorted(cal["pais"].unique()), default=sorted(cal["pais"].unique()))
    categorias = st.multiselect("Categoria", options=sorted(cal["categoria"].unique()), default=sorted(cal["categoria"].unique()))

hoje = pd.Timestamp.today().normalize()
proximos = cal[(cal["data"] >= hoje) & cal["pais"].isin(paises) & cal["categoria"].isin(categorias)]
proximos = proximos.sort_values("data").copy()

if proximos.empty:
    st.info("Nenhum evento futuro para os filtros selecionados.")
else:
    proximos["Confirmação"] = proximos["status"].map({"confirmado": "✅ confirmado", "estimado": "⏳ estimado"}).fillna(proximos["status"])
    proximos["Data"] = proximos["data"].dt.date

    tabela = proximos[["Data", "hora", "pais", "categoria", "evento", "fonte", "Confirmação"]].rename(
        columns={"hora": "Hora", "pais": "País", "categoria": "Categoria", "evento": "Evento", "fonte": "Fonte"}
    )
    st.dataframe(tabela, hide_index=True, width="stretch")

    n_estimados = (proximos["status"] == "estimado").sum()
    if n_estimados:
        st.caption(
            f"⏳ {n_estimados} evento(s) com data estimada (a partir de calendário curado manualmente, "
            "não de fonte oficial em tempo real) — sujeitos a confirmação mais próxima da data."
        )

st.caption(
    "Fontes: BCB (Copom), IBGE (IPCA/INPC/PNAD Contínua), Federal Reserve (FOMC) e BLS "
    "(CPI e Employment Situation). Datas futuras do Copom e do BLS vêm de um calendário mantido "
    "manualmente — ver README para a cadência de atualização."
)
