import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    PATH_PETROLEO_FUTUROS,
    PATH_PETROLEO_SPOT,
    load_petroleo_futuros,
    load_petroleo_spot,
    valor_mais_recente,
)

st.set_page_config(page_title="Petróleo — Macro Dashboard", page_icon="🛢️", layout="wide")
st.title("🛢️ Petróleo — spot e curva futura")

if not PATH_PETROLEO_SPOT.exists():
    st.error("Sem dados. Rode `python scripts/fetch_petroleo.py`.")
else:
    spot = load_petroleo_spot()
    data_wti, wti = valor_mais_recente(spot, "data", "ativo", "WTI", "preco_fechamento")
    data_brent, brent = valor_mais_recente(spot, "data", "ativo", "Brent", "preco_fechamento")

    col1, col2 = st.columns(2)
    col1.metric("WTI", f"US$ {wti:.2f}" if wti is not None else "—", help=f"Referência: {data_wti.date() if data_wti is not None else '—'}")
    col2.metric("Brent", f"US$ {brent:.2f}" if brent is not None else "—", help=f"Referência: {data_brent.date() if data_brent is not None else '—'}")

    st.subheader("Evolução do preço à vista")
    fig_spot = px.line(
        spot, x="data", y="preco_fechamento", color="ativo",
        labels={"data": "Data", "preco_fechamento": "Preço (US$/barril)", "ativo": "Ativo"},
    )
    st.plotly_chart(fig_spot, use_container_width=True)

st.subheader("Curva futura")
if not PATH_PETROLEO_FUTUROS.exists():
    st.error("Sem dados. Rode `python scripts/fetch_petroleo.py`.")
else:
    futuros = load_petroleo_futuros()
    capturas_disponiveis = sorted(futuros["data_captura"].unique(), reverse=True)
    captura_selecionada = st.selectbox(
        "Curva capturada em", options=capturas_disponiveis,
        format_func=lambda d: pd.Timestamp(d).date().isoformat(),
    )
    curva = futuros[futuros["data_captura"] == captura_selecionada].sort_values("mes_vencimento")

    if curva.empty:
        st.info("Nenhum contrato futuro resolvido para essa data de captura.")
    else:
        fig_curva = px.line(
            curva, x="mes_vencimento", y="preco", color="ativo", markers=True, text="contrato",
            labels={"mes_vencimento": "Vencimento", "preco": "Preço (US$/barril)", "ativo": "Ativo"},
        )
        fig_curva.update_traces(textposition="top center")
        st.plotly_chart(fig_curva, use_container_width=True)

        for ativo in curva["ativo"].unique():
            n = (curva["ativo"] == ativo).sum()
            st.caption(f"{ativo}: {n} vencimento(s) na curva.")

st.caption(
    "Fonte: Yahoo Finance (yfinance) — WTI (CL=F) e Brent (BZ=F). Símbolos de contrato futuro seguem "
    "a convenção {raiz}{código do mês}{ano}; contratos sem liquidez ou ainda não listados não aparecem na curva."
)
