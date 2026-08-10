"""
Captura diária da Estrutura a Termo das Taxas de Juros (ETTJ) da ANBIMA
(https://www.anbima.com.br/informacoes/est-termo/CZ.asp) e acumula o
histórico em data/ettj_anbima_historico.parquet.

Essa curva (ETTJ IPCA + ETTJ PRE + inflação implícita) é a curva de juros
de referência do Brasil usada no dashboard.

Uso:
    python scripts/fetch_ettj_anbima.py
    python scripts/fetch_ettj_anbima.py --dias 10
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DEST_PARQUET = ROOT / "data" / "ettj_anbima_historico.parquet"

DOWNLOAD_URL = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
DIAS_UTEIS_PADRAO = 5

CABECALHO_TABELA = "Vertices;ETTJ IPCA;ETTJ PREF;Inflação Implícita"


def _num_br(texto: str) -> float:
    texto = texto.strip()
    if not texto or texto == "--":
        return float("nan")
    return float(texto.replace(".", "").replace(",", "."))


def baixar_ettj(dia: date) -> str | None:
    body = {"Idioma": "PT", "Dt_Ref": dia.strftime("%d/%m/%Y"), "saida": "csv"}
    resp = requests.post(DOWNLOAD_URL, data=body, timeout=20)
    resp.raise_for_status()
    texto = resp.content.decode("latin-1")
    if CABECALHO_TABELA not in texto:
        return None
    return texto


def parsear_ettj(texto: str) -> pd.DataFrame:
    linhas = texto.splitlines()

    data_ref = pd.to_datetime(linhas[0].split(";")[0], format="%d/%m/%Y")

    inicio = linhas.index(CABECALHO_TABELA) + 1
    registros = []
    for linha in linhas[inicio:]:
        if not linha.strip():
            break
        campos = linha.split(";")
        registros.append(
            {
                "vertice_dias": _num_br(campos[0]),
                "ettj_ipca": _num_br(campos[1]),
                "ettj_pre": _num_br(campos[2]),
                "inflacao_implicita": _num_br(campos[3]),
            }
        )

    df = pd.DataFrame(registros)
    df["vertice_anos"] = df["vertice_dias"] / 252
    df["data"] = data_ref
    return df


def salvar_historico(novo: pd.DataFrame) -> pd.DataFrame:
    if DEST_PARQUET.exists():
        existente = pd.read_parquet(DEST_PARQUET)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo

    combinado = combinado.drop_duplicates(subset=["data", "vertice_dias"], keep="last")
    combinado = combinado.sort_values(["data", "vertice_dias"]).reset_index(drop=True)

    DEST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(DEST_PARQUET, index=False)
    return combinado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dias", type=int, default=DIAS_UTEIS_PADRAO,
        help="Quantos dias úteis recentes tentar baixar (padrão: %(default)s)",
    )
    args = parser.parse_args()

    lotes: list[pd.DataFrame] = []
    dias_uteis = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=args.dias)

    for ts in dias_uteis:
        dia = ts.date()
        texto = baixar_ettj(dia)
        if texto is None:
            print(f"{dia}: curva indisponível")
            continue
        df = parsear_ettj(texto)
        if df.empty:
            print(f"{dia}: arquivo baixado mas sem vértices")
            continue
        lotes.append(df)
        print(f"{dia}: {len(df):,} vértices (data no arquivo: {df['data'].iloc[0].date()})")

    if not lotes:
        print("Nada novo para salvar.")
        return

    total = salvar_historico(pd.concat(lotes, ignore_index=True))
    print(f"Histórico atualizado: {DEST_PARQUET} ({len(total):,} linhas, {total['data'].nunique()} dias)")


if __name__ == "__main__":
    main()
