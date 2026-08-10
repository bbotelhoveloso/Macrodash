"""
Captura diária das taxas de juros dos EUA: curva de yields do Tesouro
(Treasury.gov) e taxas de referência do mercado interbancário — Fed Funds
efetivo (EFFR) e SOFR — via API pública do NY Fed. Nenhuma das duas fontes
exige autenticação, mas ambas bloqueiam requisições sem um User-Agent de
navegador.

Uso:
    python scripts/fetch_juros_eua.py
    python scripts/fetch_juros_eua.py --meses 2
"""

from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DEST_CURVA = ROOT / "data" / "juros_eua_historico.parquet"
DEST_FED_SOFR = ROOT / "data" / "fed_funds_sofr_historico.parquet"

URL_TREASURY = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{ano}/all"
    "?type=daily_treasury_yield_curve&field_tdr_date_value_month={ano_mes}&page&_format=csv"
)
URL_NYFED_LATEST = "https://markets.newyorkfed.org/api/rates/all/latest.json"
URL_NYFED_SEARCH = "https://markets.newyorkfed.org/api/rates/all/search.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

MESES_PADRAO = 1
TIPOS_NYFED = {"EFFR", "SOFR", "OBFR", "TGCR", "BGCR"}


def baixar_curva_treasury(ano_mes: str) -> pd.DataFrame:
    ano = ano_mes[:4]
    url = URL_TREASURY.format(ano=ano, ano_mes=ano_mes)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")

    colunas_tenor = [c for c in df.columns if c != "Date"]
    longo = df.melt(id_vars="Date", value_vars=colunas_tenor, var_name="tenor_label", value_name="taxa")
    longo = longo.dropna(subset=["taxa"])

    def _vertice_anos(label: str) -> float:
        m = re.match(r"(\d+\.?\d*)\s*(Mo|Yr)", label)
        if not m:
            return float("nan")
        valor, unidade = float(m.group(1)), m.group(2)
        return valor / 12 if unidade == "Mo" else valor

    longo["vertice_anos"] = longo["tenor_label"].map(_vertice_anos)
    longo = longo.rename(columns={"Date": "data"})
    return longo[["data", "tenor_label", "vertice_anos", "taxa"]]


def baixar_fed_sofr_recente() -> pd.DataFrame:
    resp = requests.get(URL_NYFED_LATEST, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    itens = resp.json()["refRates"]
    registros = [
        {
            "data": pd.to_datetime(item["effectiveDate"]),
            "tipo": item["type"],
            "taxa": item.get("percentRate"),
            "volume_bilhoes_usd": item.get("volumeInBillions"),
        }
        for item in itens
        if item["type"] in TIPOS_NYFED and item.get("percentRate") is not None
    ]
    return pd.DataFrame(registros)


def salvar_historico(destino: Path, novo: pd.DataFrame, subset: list[str], ordenar_por: list[str]) -> pd.DataFrame:
    if destino.exists():
        existente = pd.read_parquet(destino)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo

    combinado = combinado.drop_duplicates(subset=subset, keep="last")
    combinado = combinado.sort_values(ordenar_por).reset_index(drop=True)

    destino.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(destino, index=False)
    return combinado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--meses", type=int, default=MESES_PADRAO,
        help="Quantos meses (incluindo o atual) buscar na curva do Tesouro (padrão: %(default)s)",
    )
    args = parser.parse_args()

    meses_alvo = pd.period_range(end=pd.Timestamp.today(), periods=args.meses, freq="M")
    lotes_curva = []
    for periodo in meses_alvo:
        ano_mes = periodo.strftime("%Y%m")
        try:
            df = baixar_curva_treasury(ano_mes)
        except requests.HTTPError as exc:
            print(f"{ano_mes}: erro ao baixar curva do Tesouro ({exc})")
            continue
        lotes_curva.append(df)
        print(f"{ano_mes}: {df['data'].nunique()} dias de curva do Tesouro")

    if lotes_curva:
        total_curva = salvar_historico(
            DEST_CURVA, pd.concat(lotes_curva, ignore_index=True),
            subset=["data", "tenor_label"], ordenar_por=["data", "vertice_anos"],
        )
        print(f"Curva do Tesouro atualizada: {DEST_CURVA} ({len(total_curva):,} linhas)")

    fed_sofr = baixar_fed_sofr_recente()
    if not fed_sofr.empty:
        total_fed_sofr = salvar_historico(
            DEST_FED_SOFR, fed_sofr, subset=["data", "tipo"], ordenar_por=["tipo", "data"],
        )
        print(f"EFFR/SOFR atualizado: {DEST_FED_SOFR} ({len(total_fed_sofr):,} linhas)")


if __name__ == "__main__":
    main()
