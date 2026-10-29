"""
Carrega os arquivos de data/tratado/ no SQL Server e monta o modelo estrela.

Passos:
  1. roda os scripts de sql/ (banco, staging, modelo, procedures e views);
  2. copia cada CSV tratado para a tabela stg de mesmo nome;
  3. executa dw.sp_carregar_dw;
  4. executa dw.sp_testes_qualidade e mostra o resultado.

Uso:   python python/carregar_sql.py
       python python/carregar_sql.py --servidor "localhost\\SQLEXPRESS"
Requer o SQL Server com autenticação do Windows e o pacote pyodbc.
"""
from __future__ import annotations

import argparse
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyodbc

RAIZ = Path(__file__).resolve().parents[1]
TRATADO = RAIZ / "data" / "tratado"
SQL = RAIZ / "sql"
BANCO = "DistribuidoraSul"


def escolher_driver() -> str:
    """Usa o driver ODBC mais novo instalado; o 'SQL Server' antigo vem em todo Windows."""
    modernos = sorted(d for d in pyodbc.drivers() if re.match(r"ODBC Driver \d+ for SQL Server", d))
    return modernos[-1] if modernos else "SQL Server"


def conectar(servidor: str, banco: str, driver: str, autocommit: bool = True) -> pyodbc.Connection:
    texto = (f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={banco};"
             "Trusted_Connection=yes;TrustServerCertificate=yes")
    return pyodbc.connect(texto, autocommit=autocommit)


def rodar_scripts(servidor: str, driver: str):
    conexao = conectar(servidor, "master", driver)
    cursor = conexao.cursor()
    for arquivo in sorted(SQL.glob("*.sql")):
        lotes = re.split(r"^\s*GO\s*$", arquivo.read_text(encoding="utf-8"), flags=re.MULTILINE | re.IGNORECASE)
        for lote in lotes:
            if lote.strip():
                cursor.execute(lote)
        print(f"  {arquivo.name}")
    conexao.close()


def conversor(tipo_sql: str):
    if tipo_sql in ("int", "smallint", "tinyint", "bigint"):
        return int
    if tipo_sql in ("decimal", "numeric"):
        return Decimal
    if tipo_sql == "date":
        return date.fromisoformat
    return str


def carregar_staging(conexao: pyodbc.Connection, rapido: bool):
    """Cada tabela é truncada e carregada numa transação só (com autocommit a carga fica ~10x mais lenta)."""
    cursor = conexao.cursor()
    cursor.fast_executemany = rapido
    for arquivo in sorted(TRATADO.glob("*.csv")):
        tabela = arquivo.stem
        tipos = dict(cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = 'stg' AND TABLE_NAME = ?", tabela).fetchall())
        df = pd.read_csv(arquivo, dtype=str, keep_default_na=False)
        funcoes = [conversor(tipos[c]) for c in df.columns]
        linhas = [tuple(None if v == "" else f(v) for f, v in zip(funcoes, linha))
                  for linha in df.itertuples(index=False, name=None)]
        cursor.execute(f"TRUNCATE TABLE stg.{tabela}")
        colunas = ", ".join(df.columns)
        marcadores = ", ".join("?" * len(df.columns))
        cursor.executemany(f"INSERT INTO stg.{tabela} ({colunas}) VALUES ({marcadores})", linhas)
        conexao.commit()
        print(f"  stg.{tabela:<20} {len(linhas):>8,} linhas")


def imprimir(cursor: pyodbc.Cursor):
    colunas = [c[0] for c in cursor.description]
    linhas = cursor.fetchall()
    larguras = [max(len(str(x)) for x in [c, *[ln[i] for ln in linhas]]) for i, c in enumerate(colunas)]
    print("  " + "  ".join(c.ljust(w) for c, w in zip(colunas, larguras)))
    for ln in linhas:
        print("  " + "  ".join(str(x).ljust(w) for x, w in zip(ln, larguras)))
    return linhas


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--servidor", default=r"localhost\SQLEXPRESS")
    args = parser.parse_args()

    driver = escolher_driver()
    print(f"Driver ODBC: {driver} | servidor: {args.servidor}")
    print("1. Criando banco, tabelas, procedures e views...")
    rodar_scripts(args.servidor, driver)

    print("2. Copiando os arquivos tratados para o staging...")
    staging = conectar(args.servidor, BANCO, driver, autocommit=False)
    carregar_staging(staging, rapido=driver != "SQL Server")
    staging.close()

    conexao = conectar(args.servidor, BANCO, driver)
    cursor = conexao.cursor()
    print("3. Montando o modelo estrela (dw.sp_carregar_dw)...")
    imprimir(cursor.execute("EXEC dw.sp_carregar_dw"))
    print("4. Testes de qualidade (dw.sp_testes_qualidade)...")
    resultado = imprimir(cursor.execute("EXEC dw.sp_testes_qualidade"))
    falhas = sum(1 for ln in resultado if ln.resultado != "OK")
    print("Tudo certo." if falhas == 0 else f"{falhas} teste(s) falharam: revise antes de usar no Power BI.")
    conexao.close()


if __name__ == "__main__":
    main()
