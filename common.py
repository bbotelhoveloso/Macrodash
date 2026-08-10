"""Carregamento de dados compartilhado entre app.py e as páginas do dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

PATH_JUROS_BR = DATA / "juros_brasil_historico.parquet"
PATH_ETTJ = DATA / "ettj_anbima_historico.parquet"
PATH_JUROS_EUA = DATA / "juros_eua_historico.parquet"
PATH_FED_SOFR = DATA / "fed_funds_sofr_historico.parquet"
PATH_PETROLEO_SPOT = DATA / "petroleo_spot_historico.parquet"
PATH_PETROLEO_FUTUROS = DATA / "petroleo_futuros_historico.parquet"
PATH_CALENDARIO = DATA / "calendario_economico.parquet"


@st.cache_data
def load_juros_brasil() -> pd.DataFrame:
    return pd.read_parquet(PATH_JUROS_BR)


@st.cache_data
def load_ettj() -> pd.DataFrame:
    return pd.read_parquet(PATH_ETTJ)


@st.cache_data
def load_juros_eua() -> pd.DataFrame:
    return pd.read_parquet(PATH_JUROS_EUA)


@st.cache_data
def load_fed_sofr() -> pd.DataFrame:
    return pd.read_parquet(PATH_FED_SOFR)


@st.cache_data
def load_petroleo_spot() -> pd.DataFrame:
    return pd.read_parquet(PATH_PETROLEO_SPOT)


@st.cache_data
def load_petroleo_futuros() -> pd.DataFrame:
    return pd.read_parquet(PATH_PETROLEO_FUTUROS)


@st.cache_data
def load_calendario() -> pd.DataFrame:
    return pd.read_parquet(PATH_CALENDARIO)


def valor_mais_recente(df: pd.DataFrame, col_data: str, col_filtro: str, filtro, col_valor: str):
    """Retorna (data, valor) do registro mais recente de df filtrado por col_filtro == filtro."""
    sub = df[df[col_filtro] == filtro]
    if sub.empty:
        return None, None
    linha = sub.sort_values(col_data).iloc[-1]
    return linha[col_data], linha[col_valor]


def linha_status(fonte: str, script: str, referencia) -> dict:
    """Uma linha do painel 'fontes de dados e última atualização'.

    `referencia` é o timestamp mais recente disponível para essa fonte —
    pode estar no futuro (ex.: série de meta Selic, que replica o valor
    vigente para dias seguintes) ou representar apenas o horário do último
    fetch (ex.: calendário econômico, cujas datas são eventos futuros).
    """
    if referencia is None or pd.isna(referencia):
        return {
            "Fonte": fonte,
            "Última referência": "—",
            "Dias úteis desde a última captura": "—",
            "Script de captura": script,
        }
    hoje = pd.Timestamp.today().normalize()
    referencia = pd.Timestamp(referencia).normalize()
    if referencia > hoje:
        dias_uteis_atras = 0
    else:
        dias_uteis_atras = len(pd.bdate_range(start=referencia + pd.Timedelta(days=1), end=hoje))
    return {
        "Fonte": fonte,
        "Última referência": referencia.date().isoformat(),
        "Dias úteis desde a última captura": dias_uteis_atras,
        "Script de captura": script,
    }


def painel_fontes() -> None:
    with st.expander("📊 Fontes de dados e última atualização"):
        linhas = []

        if PATH_JUROS_BR.exists():
            df = load_juros_brasil()
            linhas.append(linha_status("BCB SGS — Selic meta / CDI", "scripts/fetch_juros_brasil.py", df["data"].max()))
        if PATH_ETTJ.exists():
            df = load_ettj()
            linhas.append(linha_status("ANBIMA — ETTJ (curva de juros BR)", "scripts/fetch_ettj_anbima.py", df["data"].max()))
        if PATH_JUROS_EUA.exists():
            df = load_juros_eua()
            linhas.append(linha_status("Treasury.gov — curva de juros EUA", "scripts/fetch_juros_eua.py", df["data"].max()))
        if PATH_FED_SOFR.exists():
            df = load_fed_sofr()
            linhas.append(linha_status("NY Fed — EFFR / SOFR", "scripts/fetch_juros_eua.py", df["data"].max()))
        if PATH_PETROLEO_SPOT.exists():
            df = load_petroleo_spot()
            linhas.append(linha_status("Yahoo Finance — petróleo (spot)", "scripts/fetch_petroleo.py", df["data"].max()))
        if PATH_PETROLEO_FUTUROS.exists():
            df = load_petroleo_futuros()
            linhas.append(linha_status("Yahoo Finance — petróleo (futuros)", "scripts/fetch_petroleo.py", df["data_captura"].max()))
        if PATH_CALENDARIO.exists():
            df = load_calendario()
            br = df[df["pais"] == "BR"]
            us = df[df["pais"] == "US"]
            if not br.empty:
                linhas.append(linha_status("Calendário econômico — Brasil (IBGE/BCB)", "scripts/fetch_calendario_brasil.py", br["atualizado_em"].max()))
            if not us.empty:
                linhas.append(linha_status("Calendário econômico — EUA (Fed/BLS)", "scripts/fetch_calendario_eua.py", us["atualizado_em"].max()))

        if not linhas:
            st.info("Nenhum dado capturado ainda. Rode os scripts em scripts/fetch_*.py.")
            return

        df_status = pd.DataFrame(linhas)
        st.dataframe(df_status, hide_index=True, width="stretch")

        atrasos = [
            linha["Fonte"] for linha in linhas
            if isinstance(linha["Dias úteis desde a última captura"], int)
            and linha["Dias úteis desde a última captura"] > 2
        ]
        if atrasos:
            st.warning(
                "Mais de 2 dias úteis sem captura nova: " + ", ".join(atrasos) + ". "
                "Vale conferir se a tarefa agendada (local) ou o GitHub Actions estão rodando."
            )
