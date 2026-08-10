# Sobe o Macro Dashboard.
# Uso: clique com o botão direito > "Executar com PowerShell", ou rode `.\run.ps1` no terminal.

Set-Location $PSScriptRoot
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
