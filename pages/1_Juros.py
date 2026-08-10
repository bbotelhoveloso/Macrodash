import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    PATH_ETTJ,
    PATH_FED_SOFR,
    PATH_JUROS_BR,
    PATH_JUROS_EUA,
    load_ettj,
    load_fed_sofr,
    load_juros_brasil,
    load_juros_eua,
    valor_mais_recente,
)

st.set_page_config(page_title="Juros — Macro Dashboard", page_icon="💰", layout="wide")
st.title("💰 Juros e curva de juros")

col_br, col_eua = st.columns(2)

with col_br:
    st.header("🇧🇷 Brasil")

    if not PATH_JUROS_BR.exists():
        st.error("Sem dados. Rode `python scripts/fetch_juros_brasil.py`.")
    else:
        juros_br = load_juros_brasil()
        data_selic, selic = valor_mais_recente(juros_br, "data", "serie", "selic_meta", "valor")
        data_cdi, cdi = valor_mais_recente(juros_br, "data", "serie", "cdi", "valor")

        m1, m2 = st.columns(2)
        m1.metric("Selic meta", f"{selic:.2f}%" if selic is not None else "—", help=f"Referência: {data_selic.date() if data_selic is not None else '—'}")
        m2.metric("CDI", f"{cdi:.2f}%" if cdi is not None else "—", help=f"Referência: {data_cdi.date() if data_cdi is not None else '—'}")

        st.subheader("Evolução histórica")
        fig = px.line(
            juros_br, x="data", y="valor", color="serie",
            labels={"data": "Data", "valor": "Taxa (% a.a.)", "serie": "Série"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Curva de juros (ETTJ ANBIMA)")
    if not PATH_ETTJ.exists():
        st.error("Sem dados. Rode `python scripts/fetch_ettj_anbima.py`.")
    else:
        ettj = load_ettj()
        datas_disponiveis = sorted(ettj["data"].unique(), reverse=True)
        datas_selecionadas = st.multiselect(
            "Datas da curva", options=datas_disponiveis,
            default=datas_disponiveis[:1], format_func=lambda d: pd.Timestamp(d).date().isoformat(),
            key="ettj_datas",
        )
        curva = ettj[ettj["data"].isin(datas_selecionadas)].sort_values("vertice_anos")
        curva_long = curva.melt(
            id_vars=["data", "vertice_anos"], value_vars=["ettj_pre", "ettj_ipca"],
            var_name="curva", value_name="taxa",
        ).dropna(subset=["taxa"])
        curva_long["data_label"] = curva_long["data"].dt.date.astype(str) + " — " + curva_long["curva"].map(
            {"ettj_pre": "PRE", "ettj_ipca": "IPCA+"}
        )
        fig_curva = px.line(
            curva_long, x="vertice_anos", y="taxa", color="data_label", markers=True,
            labels={"vertice_anos": "Vértice (anos)", "taxa": "Taxa (%)", "data_label": "Curva"},
        )
        st.plotly_chart(fig_curva, use_container_width=True)

with col_eua:
    st.header("🇺🇸 EUA")

    if not PATH_FED_SOFR.exists():
        st.error("Sem dados. Rode `python scripts/fetch_juros_eua.py`.")
    else:
        fed_sofr = load_fed_sofr()
        data_effr, effr = valor_mais_recente(fed_sofr, "data", "tipo", "EFFR", "taxa")
        data_sofr, sofr = valor_mais_recente(fed_sofr, "data", "tipo", "SOFR", "taxa")

        m1, m2 = st.columns(2)
        m1.metric("Fed Funds (EFFR)", f"{effr:.2f}%" if effr is not None else "—", help=f"Referência: {data_effr.date() if data_effr is not None else '—'}")
        m2.metric("SOFR", f"{sofr:.2f}%" if sofr is not None else "—", help=f"Referência: {data_sofr.date() if data_sofr is not None else '—'}")

        st.subheader("Evolução histórica")
        fig = px.line(
            fed_sofr, x="data", y="taxa", color="tipo",
            labels={"data": "Data", "taxa": "Taxa (% a.a.)", "tipo": "Taxa"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Curva de juros (Treasury)")
    if not PATH_JUROS_EUA.exists():
        st.error("Sem dados. Rode `python scripts/fetch_juros_eua.py`.")
    else:
        curva_eua = load_juros_eua()
        datas_disponiveis_eua = sorted(curva_eua["data"].unique(), reverse=True)
        datas_selecionadas_eua = st.multiselect(
            "Datas da curva", options=datas_disponiveis_eua,
            default=datas_disponiveis_eua[:1], format_func=lambda d: pd.Timestamp(d).date().isoformat(),
            key="treasury_datas",
        )
        curva_filtrada = curva_eua[curva_eua["data"].isin(datas_selecionadas_eua)].sort_values("vertice_anos")
        curva_filtrada = curva_filtrada.assign(data_label=curva_filtrada["data"].dt.date.astype(str))
        fig_curva_eua = px.line(
            curva_filtrada, x="vertice_anos", y="taxa", color="data_label", markers=True,
            labels={"vertice_anos": "Vértice (anos)", "taxa": "Taxa (%)", "data_label": "Data"},
        )
        st.plotly_chart(fig_curva_eua, use_container_width=True)

st.caption(
    "Brasil: Selic/CDI via BCB SGS, curva via ETTJ ANBIMA (fecha ao fim do dia, horário de Brasília). "
    "EUA: EFFR/SOFR via NY Fed, curva via Treasury.gov (horário de Nova York)."
)
