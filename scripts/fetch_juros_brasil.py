"""
Captura diária das taxas de juros vigentes do Brasil (Selic meta e CDI) via
Sistema Gerenciador de Séries Temporais (SGS) do Banco Central.

API pública, sem autenticação: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados

Uso:
    python scripts/fetch_juros_brasil.py
    python scripts/fetch_juros_brasil.py --dias 30
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DEST_PARQUET = ROOT / "data" / "juros_brasil_historico.parquet"

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json"

# código da série SGS -> nome usado no dataset
SERIES = {
    432: "selic_meta",
    4389: "cdi",
}

DIAS_PADRAO = 15


def baixar_serie(codigo: int, n: int) -> pd.DataFrame:
    resp = requests.get(URL_SGS.format(codigo=codigo, n=n), timeout=20)
    resp.raise_for_status()
    dados = resp.json()
    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = df["valor"].astype(float)
    df["serie"] = SERIES[codigo]
    return df[["data", "serie", "valor"]]


def salvar_historico(novo: pd.DataFrame) -> pd.DataFrame:
    if DEST_PARQUET.exists():
        existente = pd.read_parquet(DEST_PARQUET)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo

    combinado = combinado.drop_duplicates(subset=["data", "serie"], keep="last")
    combinado = combinado.sort_values(["serie", "data"]).reset_index(drop=True)

    DEST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(DEST_PARQUET, index=False)
    return combinado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dias", type=int, default=DIAS_PADRAO,
        help="Quantos registros recentes buscar por série (padrão: %(default)s)",
    )
    args = parser.parse_args()

    lotes = []
    for codigo in SERIES:
        df = baixar_serie(codigo, args.dias)
        lotes.append(df)
        print(f"{SERIES[codigo]}: {len(df)} registros (último: {df['data'].max().date()} = {df['valor'].iloc[-1]:.2f}%)")

    total = salvar_historico(pd.concat(lotes, ignore_index=True))
    print(f"Histórico atualizado: {DEST_PARQUET} ({len(total):,} linhas)")


if __name__ == "__main__":
    main()
