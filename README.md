# Macro Dashboard

Dashboard de indicadores macroeconômicos: juros e curva de juros (Brasil e EUA),
preço do petróleo e curva futura, e calendário econômico (inflação, emprego e
juros — Brasil e EUA).

## Rodar localmente

```
.\run.ps1
```

ou

```
.venv\Scripts\python.exe -m streamlit run app.py
```

## Fontes de dados

| Fonte | Script | Frequência |
|---|---|---|
| BCB SGS (Selic meta, CDI) | `scripts/fetch_juros_brasil.py` | diária, automática |
| ANBIMA ETTJ (curva de juros BR) | `scripts/fetch_ettj_anbima.py` | diária, automática |
| Treasury.gov (curva de juros EUA) | `scripts/fetch_juros_eua.py` | diária, automática |
| NY Fed (Fed Funds efetivo / SOFR) | `scripts/fetch_juros_eua.py` | diária, automática |
| yfinance (petróleo WTI/Brent, spot e futuros) | `scripts/fetch_petroleo.py` | diária, automática |
| IBGE (calendário IPCA/INPC/PNAD Contínua) | `scripts/fetch_calendario_brasil.py` | diária, automática |
| BCB (Copom — reuniões já realizadas) | `scripts/fetch_calendario_brasil.py` | diária, automática |
| **Copom — datas futuras** | `data/copom_calendario_seed.csv` | **manual, ~1x/ano (quando o BCB anuncia o calendário do ano seguinte, geralmente em junho)** |
| Federal Reserve (calendário FOMC) | `scripts/fetch_calendario_eua.py` | diária, automática (scrape) |
| **BLS — CPI e Employment Situation** | `data/bls_calendario_seed.csv` | **manual, ~1x/ano (o BLS publica o calendário do ano seguinte por volta de outubro; bls.gov bloqueia scraping automatizado com 403)** |

A captura automática roda diariamente via GitHub Actions
(`.github/workflows/fetch_macro.yml`). Os dois arquivos `*_seed.csv` marcados
como manuais precisam ser atualizados à mão quando cada instituição publica o
calendário do próximo ano — o resto dos dados é 100% automático.

**Atenção:** as datas em `copom_calendario_seed.csv` e `bls_calendario_seed.csv`
foram preenchidas com estimativas (padrão histórico de cadência das reuniões/
divulgações), não com o calendário oficial — todas marcadas `status=estimado`.
Substitua pelas datas oficiais assim que BCB/BLS publicarem o calendário do
período correspondente.

## Riscos conhecidos

- `yfinance` é scraping não-oficial do Yahoo Finance e pode quebrar sem aviso.
- O app exibe um painel de "fontes de dados e última atualização" com aviso
  quando alguma captura está atrasada.
