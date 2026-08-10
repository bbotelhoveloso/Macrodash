"""
Captura diária do preço do petróleo (WTI e Brent): spot e curva futura,
via Yahoo Finance (yfinance). Fonte não-oficial (scraping), mais frágil que
as demais do projeto — símbolos de contrato que não resolverem são ignorados
silenciosamente (contrato ainda não listado ou sem liquidez).

Uso:
    python scripts/fetch_petroleo.py
    python scripts/fetch_petroleo.py --meses-futuros 12
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DEST_SPOT = ROOT / "data" / "petroleo_spot_historico.parquet"
DEST_FUTUROS = ROOT / "data" / "petroleo_futuros_historico.parquet"

# WTI = NYMEX Crude Oil (CL), Brent = ICE Brent (BZ, listado no Yahoo sob sufixo .NYM)
ATIVOS_SPOT = {"CL=F": "WTI", "BZ=F": "Brent"}
RAIZ_CONTRATO = {"WTI": "CL", "Brent": "BZ"}

CODIGO_MES = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z",
}

MESES_FUTUROS_PADRAO = 15


def baixar_spot() -> pd.DataFrame:
    registros = []
    for simbolo, ativo in ATIVOS_SPOT.items():
        hist = yf.Ticker(simbolo).history(period="5d", interval="1d")
        if hist.empty:
            print(f"{ativo} ({simbolo}): sem dados de spot")
            continue
        hist = hist.reset_index()
        for _, linha in hist.iterrows():
            registros.append(
                {
                    "data": pd.Timestamp(linha["Date"]).tz_localize(None).normalize(),
                    "ativo": ativo,
                    "preco_fechamento": float(linha["Close"]),
                    "volume": float(linha["Volume"]) if pd.notna(linha["Volume"]) else None,
                }
            )
        print(f"{ativo} ({simbolo}): {len(hist)} dias de spot")
    return pd.DataFrame(registros)


def meses_vencimento(n: int) -> list[pd.Timestamp]:
    inicio = pd.Timestamp.today().normalize().replace(day=1)
    return [inicio + pd.DateOffset(months=i) for i in range(n)]


def baixar_futuros(n_meses: int) -> pd.DataFrame:
    hoje = pd.Timestamp.today().normalize()
    registros = []
    for ativo, raiz in RAIZ_CONTRATO.items():
        resolvidos = 0
        for vencimento in meses_vencimento(n_meses):
            simbolo = f"{raiz}{CODIGO_MES[vencimento.month]}{vencimento.year % 100:02d}.NYM"
            try:
                hist = yf.Ticker(simbolo).history(period="5d", interval="1d")
            except Exception:
                continue
            if hist.empty:
                continue
            preco = float(hist["Close"].dropna().iloc[-1])
            registros.append(
                {
                    "data_captura": hoje,
                    "ativo": ativo,
                    "contrato": simbolo.replace(".NYM", ""),
                    "mes_vencimento": vencimento,
                    "preco": preco,
                }
            )
            resolvidos += 1
        print(f"{ativo}: {resolvidos}/{n_meses} vencimentos resolvidos")
    return pd.DataFrame(registros)


def salvar_spot(novo: pd.DataFrame) -> pd.DataFrame:
    if DEST_SPOT.exists():
        existente = pd.read_parquet(DEST_SPOT)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo
    combinado = combinado.drop_duplicates(subset=["data", "ativo"], keep="last")
    combinado = combinado.sort_values(["ativo", "data"]).reset_index(drop=True)
    DEST_SPOT.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(DEST_SPOT, index=False)
    return combinado


def salvar_futuros(novo: pd.DataFrame) -> pd.DataFrame:
    if DEST_FUTUROS.exists():
        existente = pd.read_parquet(DEST_FUTUROS)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo
    combinado = combinado.drop_duplicates(subset=["data_captura", "ativo", "contrato"], keep="last")
    combinado = combinado.sort_values(["data_captura", "ativo", "mes_vencimento"]).reset_index(drop=True)
    DEST_FUTUROS.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(DEST_FUTUROS, index=False)
    return combinado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--meses-futuros", type=int, default=MESES_FUTUROS_PADRAO,
        help="Quantos meses à frente tentar resolver contratos futuros (padrão: %(default)s)",
    )
    args = parser.parse_args()

    spot = baixar_spot()
    if not spot.empty:
        total_spot = salvar_spot(spot)
        print(f"Spot atualizado: {DEST_SPOT} ({len(total_spot):,} linhas)")

    futuros = baixar_futuros(args.meses_futuros)
    if not futuros.empty:
        total_futuros = salvar_futuros(futuros)
        print(f"Futuros atualizados: {DEST_FUTUROS} ({len(total_futuros):,} linhas)")
    else:
        print("Nenhum contrato futuro resolvido.")


if __name__ == "__main__":
    main()
