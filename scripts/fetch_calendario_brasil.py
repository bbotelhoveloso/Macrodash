"""
Captura o calendário de divulgações econômicas do Brasil: inflação (IPCA,
IPCA-15, INPC) e emprego (PNAD Contínua mensal) via API pública do IBGE, e
reuniões do Copom (juros).

O calendário de datas FUTURAS do Copom não tem API estruturada confiável —
o BCB só expõe as reuniões já realizadas via endpoint `comunicados`. Por
isso as datas futuras vêm de data/copom_calendario_seed.csv, mantido
manualmente (atualizar quando o BCB anunciar o calendário do próximo ano,
normalmente em junho). Este script confirma/complementa com as reuniões já
realizadas via API.

Uso:
    python scripts/fetch_calendario_brasil.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DEST_PARQUET = ROOT / "data" / "calendario_economico.parquet"
COPOM_SEED_CSV = ROOT / "data" / "copom_calendario_seed.csv"

URL_IBGE_CALENDARIO = "https://servicodados.ibge.gov.br/api/v3/calendario/?qtd=5000"
URL_COPOM_COMUNICADOS = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=40"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# nome_produto no IBGE usa o nome por extenso, não a sigla (ex.: "Índice
# Nacional de Preços ao Consumidor Amplo", não "IPCA") — a classificação
# abaixo é por palavra-chave no título, não por produto_id (parâmetro de
# filtro da API se mostrou pouco confiável em testes).
PALAVRAS_INFLACAO = ["Consumidor"]
PALAVRAS_EMPREGO_NOME_PRODUTO = ["pnadc1"]  # "Divulgação mensal#pnadc1" = PNAD Contínua mensal


def baixar_calendario_ibge() -> pd.DataFrame:
    resp = requests.get(URL_IBGE_CALENDARIO, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    items = resp.json()["items"]

    registros = []
    for item in items:
        titulo = item.get("titulo") or ""
        nome_produto = item.get("nome_produto") or ""

        if any(p in titulo for p in PALAVRAS_INFLACAO):
            categoria = "Inflação"
        elif any(p in nome_produto for p in PALAVRAS_EMPREGO_NOME_PRODUTO):
            categoria = "Emprego"
        else:
            continue

        dt = pd.to_datetime(item["data_divulgacao"], format="%d/%m/%Y %H:%M:%S")
        registros.append(
            {
                "data": dt.normalize(),
                "hora": dt.strftime("%H:%M"),
                "pais": "BR",
                "categoria": categoria,
                "evento": titulo,
                "fonte": "IBGE",
                "status": "confirmado",
                "link": item.get("link") or "https://www.ibge.gov.br/calendario-de-divulgacoes.html",
            }
        )
    return pd.DataFrame(registros)


def baixar_copom_realizadas() -> pd.DataFrame:
    resp = requests.get(URL_COPOM_COMUNICADOS, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    itens = resp.json()["conteudo"]

    registros = [
        {
            "data": pd.to_datetime(item["dataReferencia"]).normalize(),
            "hora": pd.NA,
            "pais": "BR",
            "categoria": "Juros",
            "evento": "Reunião do Copom",
            "fonte": "BCB",
            "status": "confirmado",
            "link": "https://www.bcb.gov.br/publicacoes/atascopom",
        }
        for item in itens
    ]
    return pd.DataFrame(registros)


def carregar_copom_seed() -> pd.DataFrame:
    if not COPOM_SEED_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(COPOM_SEED_CSV)
    df["data"] = pd.to_datetime(df["data"]).dt.normalize()
    df["pais"] = "BR"
    return df


def salvar_calendario(novo: pd.DataFrame) -> pd.DataFrame:
    novo["atualizado_em"] = pd.Timestamp.now()

    if DEST_PARQUET.exists():
        existente = pd.read_parquet(DEST_PARQUET)
        existente_outros_paises = existente[existente["pais"] != "BR"]
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

    ibge = baixar_calendario_ibge()
    print(f"IBGE: {len(ibge)} eventos (inflação + emprego)")
    partes.append(ibge)

    # Seed (estimado) primeiro, comunicados oficiais (confirmado) depois — em
    # caso de mesma data, drop_duplicates(keep="last") em salvar_calendario()
    # mantém a versão confirmada quando uma reunião estimada já aconteceu.
    copom_seed = carregar_copom_seed()
    if not copom_seed.empty:
        print(f"Copom (seed manual, datas futuras): {len(copom_seed)} reuniões")
        partes.append(copom_seed)

    try:
        copom_realizadas = baixar_copom_realizadas()
        print(f"Copom (BCB, realizadas): {len(copom_realizadas)} reuniões")
        partes.append(copom_realizadas)
    except requests.RequestException as exc:
        print(f"Copom (BCB): erro ao buscar reuniões realizadas ({exc})")

    br = pd.concat(partes, ignore_index=True)
    total = salvar_calendario(br)
    print(f"Calendário econômico (BR) atualizado: {DEST_PARQUET} ({(total['pais'] == 'BR').sum():,} linhas BR)")


if __name__ == "__main__":
    main()
