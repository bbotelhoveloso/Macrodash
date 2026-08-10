"""
Captura o calendário de divulgações econômicas dos EUA: reuniões do FOMC
(juros) via scraping da página oficial do Federal Reserve, e inflação/emprego
(CPI e Employment Situation do BLS).

O Fed publica o calendário do FOMC com bastante antecedência (o ano corrente
e o seguinte já aparecem na página), então o scraping é a fonte primária e
funciona bem. Já o bls.gov bloqueia scraping automatizado (HTTP 403 mesmo
com header de navegador) — por isso o CPI/Employment Situation vêm de
data/bls_calendario_seed.csv, mantido manualmente (atualizar quando o BLS
publicar o calendário do próximo ano, normalmente em outubro). O scraping do
BLS abaixo é best-effort: se funcionar um dia, ótimo, mas o app não depende
dele.

Uso:
    python scripts/fetch_calendario_eua.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DEST_PARQUET = ROOT / "data" / "calendario_economico.parquet"
BLS_SEED_CSV = ROOT / "data" / "bls_calendario_seed.csv"

URL_FOMC_CALENDAR = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
URL_BLS_SCHEDULE = "https://www.bls.gov/schedule/news_release/{ano}_sched.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

MESES_EN = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

ANO_MINIMO = pd.Timestamp.today().year - 1


def _mes_decisao(mes_texto: str) -> int | None:
    """'Apr/May' -> maio (mês da decisão, sempre o último da reunião)."""
    partes = re.findall(r"[A-Za-z]+", mes_texto)
    if not partes:
        return None
    return MESES_EN.get(partes[-1])


def baixar_fomc() -> pd.DataFrame:
    resp = requests.get(URL_FOMC_CALENDAR, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    ano_atual = None
    registros = []
    for tag in soup.find_all(["h4", "div"]):
        if tag.name == "h4":
            a = tag.find("a")
            if a and "FOMC Meetings" in a.get_text():
                m = re.match(r"(\d{4})", a.get_text(strip=True))
                if m:
                    ano_atual = int(m.group(1))
            continue

        classes = tag.get("class") or []
        if "fomc-meeting__month" not in classes or ano_atual is None or ano_atual < ANO_MINIMO:
            continue

        mes_texto = tag.get_text(strip=True)
        date_div = tag.find_next_sibling("div")
        if not date_div or "fomc-meeting__date" not in (date_div.get("class") or []):
            continue

        data_texto = date_div.get_text(strip=True)
        dias = re.findall(r"\d{1,2}", data_texto)
        mes_num = _mes_decisao(mes_texto)
        if not dias or mes_num is None:
            continue

        dia_decisao = int(dias[-1])
        try:
            data = pd.Timestamp(year=ano_atual, month=mes_num, day=dia_decisao)
        except ValueError:
            continue

        com_projecoes = "*" in data_texto
        evento = "Reunião do FOMC" + (" (com projeções/SEP)" if com_projecoes else "")
        registros.append(
            {
                "data": data,
                "hora": pd.NA,
                "pais": "US",
                "categoria": "Juros",
                "evento": evento,
                "fonte": "Federal Reserve",
                "status": "confirmado",
                "link": URL_FOMC_CALENDAR,
            }
        )

    return pd.DataFrame(registros)


def baixar_bls_best_effort() -> pd.DataFrame:
    """Tentativa best-effort — bls.gov historicamente bloqueia scraping (403).
    Nunca é a única fonte: data/bls_calendario_seed.csv cobre o fallback."""
    ano = pd.Timestamp.today().year
    try:
        resp = requests.get(URL_BLS_SCHEDULE.format(ano=ano), headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"BLS scrape best-effort falhou ({exc}) — usando só o seed manual.")
        return pd.DataFrame()

    # Página respondeu: parsing não implementado (formato nunca confirmado em
    # testes por causa do bloqueio). Se um dia o acesso funcionar, é aqui que
    # o parser real entraria.
    print("BLS respondeu 200 inesperadamente — parser não implementado, ignorando (seed cobre o fallback).")
    return pd.DataFrame()


def carregar_bls_seed() -> pd.DataFrame:
    if not BLS_SEED_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(BLS_SEED_CSV)
    df["data"] = pd.to_datetime(df["data"]).dt.normalize()
    df["pais"] = "US"
    return df


def salvar_calendario(novo: pd.DataFrame) -> pd.DataFrame:
    novo["atualizado_em"] = pd.Timestamp.now()

    if DEST_PARQUET.exists():
        existente = pd.read_parquet(DEST_PARQUET)
        existente_outros_paises = existente[existente["pais"] != "US"]
        combinado = pd.concat([existente_outros_paises, novo], ignore_index=True)
    else:
        combinado = novo

    combinado = combinado.drop_duplicates(subset=["data", "pais", "evento"], keep="last")
    combinado = combinado.sort_values(["data", "pais", "categoria"]).reset_index(drop=True)

    DEST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(DEST_PARQUET, index=False)
    return combinado


def main() -> None:
    partes = []

    # Seed primeiro, fontes automáticas depois — em caso de mesma data,
    # drop_duplicates(keep="last") mantém a versão automática/confirmada.
    bls_seed = carregar_bls_seed()
    if not bls_seed.empty:
        print(f"BLS (seed manual): {len(bls_seed)} divulgações (CPI + Employment Situation)")
        partes.append(bls_seed)

    bls_scrape = baixar_bls_best_effort()
    if not bls_scrape.empty:
        partes.append(bls_scrape)

    fomc = baixar_fomc()
    print(f"FOMC (Federal Reserve, scrape): {len(fomc)} reuniões")
    partes.append(fomc)

    if not partes:
        print("Nada para salvar.")
        return

    us = pd.concat(partes, ignore_index=True)
    total = salvar_calendario(us)
    print(f"Calendário econômico (US) atualizado: {DEST_PARQUET} ({(total['pais'] == 'US').sum():,} linhas US)")


if __name__ == "__main__":
    main()
