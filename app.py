"""
Macro Dashboard — indicadores macroeconômicos: juros e curva de juros
(Brasil e EUA), preço do petróleo e curva futura, e calendário econômico.
"""

import pandas as pd
import streamlit as st

from common import (
    PATH_CALENDARIO,
    PATH_FED_SOFR,
    PATH_JUROS_BR,
    PATH_JUROS_EUA,
    PATH_PETROLEO_SPOT,
    load_calendario,
    load_fed_sofr,
    load_juros_brasil,
    load_juros_eua,
    load_petroleo_spot,
    painel_fontes,
    valor_mais_recente,
)

st.set_page_config(page_title="Macro Dashboard", page_icon="📈", layout="wide")

st.title("📈 Macro Dashboard")
st.caption("Juros e curva de juros (Brasil e EUA), petróleo (spot e curva futura) e calendário econômico.")

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

if PATH_JUROS_BR.exists():
    df = load_juros_brasil()
    data_selic, selic = valor_mais_recente(df, "data", "serie", "selic_meta", "valor")
    data_cdi, cdi = valor_mais_recente(df, "data", "serie", "cdi", "valor")
    col1.metric("Selic meta", f"{selic:.2f}%" if selic is not None else "—")
    col2.metric("CDI", f"{cdi:.2f}%" if cdi is not None else "—")
else:
    col1.metric("Selic meta", "—")
    col2.metric("CDI", "—")

if PATH_FED_SOFR.exists():
    df = load_fed_sofr()
    _, effr = valor_mais_recente(df, "data", "tipo", "EFFR", "taxa")
    _, sofr = valor_mais_recente(df, "data", "tipo", "SOFR", "taxa")
    col3.metric("Fed Funds (EFFR)", f"{effr:.2f}%" if effr is not None else "—")
    col4.metric("SOFR", f"{sofr:.2f}%" if sofr is not None else "—")
else:
    col3.metric("Fed Funds (EFFR)", "—")
    col4.metric("SOFR", "—")

if PATH_PETROLEO_SPOT.exists():
    df = load_petroleo_spot()
    _, wti = valor_mais_recente(df, "data", "ativo", "WTI", "preco_fechamento")
    _, brent = valor_mais_recente(df, "data", "ativo", "Brent", "preco_fechamento")
    col5.metric("WTI", f"US$ {wti:.2f}" if wti is not None else "—")
    col6.metric("Brent", f"US$ {brent:.2f}" if brent is not None else "—")
else:
    col5.metric("WTI", "—")
    col6.metric("Brent", "—")

st.divider()

nav1, nav2, nav3 = st.columns(3)
nav1.page_link("pages/1_Juros.py", label="Juros — Brasil e EUA", icon="💰")
nav2.page_link("pages/2_Petroleo.py", label="Petróleo — spot e curva futura", icon="🛢️")
nav3.page_link("pages/3_Calendario.py", label="Calendário econômico", icon="🗓️")

if PATH_CALENDARIO.exists():
    cal = load_calendario()
    hoje = pd.Timestamp.today().normalize()
    proximos = cal[cal["data"] >= hoje].sort_values("data")
    if not proximos.empty:
        proximo = proximos.iloc[0]
        st.caption(f"Próximo evento do calendário: {proximo['evento']} ({proximo['data'].date()}, {proximo['pais']}).")

st.divider()

painel_fontes()
