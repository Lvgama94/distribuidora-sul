"""
Gera o catálogo de indicadores a partir dos modelos semânticos do Power BI.

Lê as medidas de powerbi/*.SemanticModel (nome, descrição ///, fórmula DAX, formato e
pasta), descobre de quais tabelas do SQL cada uma depende, inclusive pelas medidas que
ela usa, e busca nas views de conferência o valor de 2025 das que foram conferidas.
Grava docs/catalogo_indicadores.md e o JSON da página indicadores.html do portfólio.
As medidas ocultas (de formatação) ficam de fora.

A definição mora no modelo: medida visível sem descrição faz o script parar.

Uso:   python python/gerar_catalogo.py
       python python/gerar_catalogo.py --pasta ../portfolio/assets/data
Requer o banco DistribuidoraSul carregado (python/carregar_sql.py).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from carregar_sql import BANCO, RAIZ, conectar, escolher_driver

PASTA_PADRAO = RAIZ.parent / "portfolio" / "assets" / "data"
DOC = RAIZ / "docs" / "catalogo_indicadores.md"
# pasta do modelo, nome do painel, página web, view de conferência
MODELOS = [
    ("Financeiro", "Financeiro", "financeiro.html", "dw.vw_conferencia_financeiro"),
    ("PeopleAnalytics", "People Analytics", "rh.html", "dw.vw_conferencia_rh"),
    ("ComprasEstoque", "Compras e Estoque", "compras.html", "dw.vw_conferencia_compras"),
    ("Comercial", "Comercial", "comercial.html", "dw.vw_conferencia_comercial"),
]
# Tabelas que filtram mas não são fonte do número
SEM_FONTE = {"Calendário", "Medidas"}

MEDIDA = re.compile(r"^\tmeasure ('(?:[^']|'')+'|[^\s=]+)\s*=(.*)$")
REF_MEDIDA = re.compile(r"(?<![\w'\]])\[([^\]]+)\]")


def nome_tmdl(texto: str) -> str:
    return texto[1:-1].replace("''", "'") if texto.startswith("'") else texto


def ler_medidas(arquivo: Path) -> list[dict]:
    """Medidas do arquivo Medidas.tmdl, com a descrição (linhas ///) que vem logo antes de cada uma."""
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    medidas, descricao, i = [], [], 0
    while i < len(linhas):
        linha = linhas[i]
        m = MEDIDA.match(linha)
        if linha.startswith("\t///"):
            descricao.append(linha[4:].strip())
            i += 1
            continue
        if not m:
            descricao = []
            i += 1
            continue
        formula = [m.group(2).strip()] if m.group(2).strip() else []
        i += 1
        # Fórmula de várias linhas: vem indentada com três tabulações
        while i < len(linhas) and (linhas[i].startswith("\t\t\t") or not linhas[i].strip()):
            formula.append(linhas[i][3:].rstrip())
            i += 1
        propriedades = {}
        while i < len(linhas) and linhas[i].startswith("\t\t"):
            chave, _, valor = linhas[i].strip().partition(":")
            propriedades[chave.strip()] = valor.strip()
            i += 1
        medidas.append({
            "nome": nome_tmdl(m.group(1)),
            "descricao": " ".join(descricao),
            "formula": "\n".join(formula).strip(),
            "formato": propriedades.get("formatString", ""),
            "pasta": propriedades.get("displayFolder", ""),
            "oculta": "isHidden" in propriedades,
        })
        descricao = []
    return medidas


def fontes_das_tabelas(pasta: Path) -> dict[str, str]:
    """Cada tabela do modelo e o objeto do SQL Server de onde ela vem (pela partição em Power Query)."""
    fontes = {}
    for arquivo in (pasta / "definition" / "tables").glob("*.tmdl"):
        texto = arquivo.read_text(encoding="utf-8")
        tabela = nome_tmdl(re.search(r"^table (.+)$", texto, re.M).group(1).strip())
        item = re.search(r'Schema\s*=\s*"(\w+)",\s*Item\s*=\s*"(\w+)"', texto) or re.search(r"\b(dw)\.(\w+)", texto)
        fontes[tabela] = f"{item.group(1)}.{item.group(2)}" if item else ""
    return fontes


def tabelas_citadas(formula: str, tabelas: set[str]) -> set[str]:
    """Tabelas do modelo citadas na fórmula, como Venda[Coluna], 'Contas a Receber'[Valor] ou COUNTROWS(Produto)."""
    # Sem textos entre aspas e sem o que está entre colchetes (colunas e medidas), sobram os nomes de tabela
    limpa = re.sub(r'"[^"]*"|\[[^\]]*\]', " ", formula)
    return {t for t in tabelas
            if f"'{t.replace(chr(39), chr(39) * 2)}'" in limpa or re.search(rf"(?<![\w'À-ÿ]){re.escape(t)}(?![\wÀ-ÿ'])", limpa)}


def formatar(valor, formato: str) -> str:
    """Valor no formato da medida, em português (R$ 1.234, 12,3%)."""
    if valor is None:
        return ""
    decimais = re.search(r"\.(0+)", formato)
    casas = len(decimais.group(1)) if decimais else 0
    if "%" in formato:
        texto, sufixo = f"{valor * 100:,.{casas}f}", "%"
    else:
        texto, sufixo = f"{valor:,.{casas}f}", ""
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".").replace("-", "−")
    return ("R$ " if "R$" in formato else "") + texto + sufixo


def montar(cursor) -> dict:
    indicadores, sem_descricao, sem_medida = [], [], []
    for pasta_modelo, painel, pagina, view in MODELOS:
        pasta = RAIZ / "powerbi" / f"{pasta_modelo}.SemanticModel"
        medidas = ler_medidas(pasta / "definition" / "tables" / "Medidas.tmdl")
        fontes = fontes_das_tabelas(pasta)
        nomes = {m["nome"] for m in medidas}
        conferidos = defaultdict(dict)
        for ano, indicador, valor in cursor.execute(f"SELECT ano, indicador, valor FROM {view}").fetchall():
            conferidos[indicador][str(ano) if ano else "posição"] = float(valor)
        sem_medida += [f"{view}: {n}" for n in conferidos if n not in nomes]

        usa = {m["nome"]: sorted({r for r in REF_MEDIDA.findall(m["formula"]) if r in nomes and r != m["nome"]}) for m in medidas}
        tabelas = {m["nome"]: tabelas_citadas(m["formula"], set(fontes)) for m in medidas}
        ocultas = {m["nome"] for m in medidas if m["oculta"]}

        def todas_as_tabelas(nome, vistas=()):
            # As tabelas de uma medida incluem as das medidas que ela usa
            resultado = set(tabelas[nome])
            for outra in usa[nome]:
                if outra not in vistas:
                    resultado |= todas_as_tabelas(outra, (*vistas, nome))
            return resultado

        for m in medidas:
            if m["oculta"]:
                continue
            if not m["descricao"]:
                sem_descricao.append(f"{painel}: {m['nome']}")
            origem = sorted(todas_as_tabelas(m["nome"]) - SEM_FONTE)
            valores = conferidos.get(m["nome"], {})
            indicadores.append({
                "painel": painel, "pagina": pagina, "pasta": m["pasta"], "nome": m["nome"],
                "descricao": m["descricao"], "formula": m["formula"], "formato": m["formato"],
                "fontes": [{"tabela": t, "sql": fontes.get(t, "")} for t in origem],
                "usa": usa[m["nome"]],
                "usado_por": sorted(o for o, refs in usa.items() if m["nome"] in refs and o not in ocultas),
                "conferido": {ano: {"valor": v, "texto": formatar(v, m["formato"])} for ano, v in valores.items()},
            })
    if sem_descricao:
        sys.exit("Medidas visíveis sem descrição no modelo:\n  " + "\n  ".join(sem_descricao))
    if sem_medida:
        sys.exit("Indicadores das views de conferência sem medida com o mesmo nome:\n  " + "\n  ".join(sem_medida))

    # Mesmo nome em mais de um modelo: mesmo cálculo ou não?
    por_nome = defaultdict(list)
    for ind in indicadores:
        por_nome[ind["nome"]].append(ind)
    homonimos = []
    for nome, lista in sorted(por_nome.items()):
        if len(lista) > 1:
            formulas = {re.sub(r"\s+", "", i["formula"]) for i in lista}
            homonimos.append({"nome": nome, "mesma_formula": len(formulas) == 1,
                              "versoes": [{"painel": i["painel"], "descricao": i["descricao"], "formula": i["formula"]} for i in lista]})
    return {"paineis": [{"nome": p, "pagina": pg, "view": v} for _, p, pg, v in MODELOS],
            "indicadores": indicadores, "homonimos": homonimos}


def celula(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def escrever_markdown(catalogo: dict) -> str:
    ind = catalogo["indicadores"]
    linhas = [
        "# Catálogo de indicadores",
        "",
        "Gerado por [`python/gerar_catalogo.py`](../python/gerar_catalogo.py) a partir dos modelos semânticos em "
        "[`powerbi/`](../powerbi). Não edite à mão: a definição de cada indicador é a descrição da medida no modelo "
        "(linha `///` no TMDL, ou a propriedade Descrição no Power BI Desktop), que é também o que aparece ao passar o "
        "mouse sobre a medida no Power BI. Para mudar uma definição, mude no modelo e gere de novo.",
        "",
        "A coluna **2025** traz o valor das medidas que foram conferidas contra as views de conferência do SQL "
        "(`dw.vw_conferencia_*`). As medidas de formatação, ocultas, ficam de fora. "
        "[Versão com busca](https://lucasgama.vercel.app/indicadores.html) no portfólio.",
        "",
        "| Painel | Indicadores | Conferidos com o SQL |",
        "|---|---:|---:|",
    ]
    for p in catalogo["paineis"]:
        doPainel = [i for i in ind if i["painel"] == p["nome"]]
        linhas.append(f"| {p['nome']} | {len(doPainel)} | {sum(1 for i in doPainel if i['conferido'])} |")
    linhas.append(f"| **Total** | **{len(ind)}** | **{sum(1 for i in ind if i['conferido'])}** |")

    if catalogo["homonimos"]:
        linhas += ["", "## Nomes repetidos entre modelos", "",
                   "O mesmo nome em mais de um modelo pede atenção: se o cálculo é diferente, o nome deveria deixar isso claro.", ""]
        for h in catalogo["homonimos"]:
            situacao = "mesma fórmula" if h["mesma_formula"] else "fórmulas diferentes"
            linhas.append(f"- **{h['nome']}** ({situacao})")
            for v in h["versoes"]:
                linhas.append(f"  - {v['painel']}: {v['descricao']} `{celula(v['formula'])}`")

    for p in catalogo["paineis"]:
        linhas += ["", f"## {p['nome']}", ""]
        pastas = sorted({i["pasta"] for i in ind if i["painel"] == p["nome"]})
        for pasta in pastas:
            linhas += [f"### {pasta}", "", "| Indicador | Definição | Fórmula DAX | Fonte | 2025 |", "|---|---|---|---|---:|"]
            for i in (x for x in ind if x["painel"] == p["nome"] and x["pasta"] == pasta):
                fonte = ", ".join(f"`{f['sql']}`" if f["sql"] else f["tabela"] for f in i["fontes"]) or "—"
                conferido = i["conferido"].get("2025") or i["conferido"].get("posição")
                valor = conferido["texto"] if conferido else ""
                linhas.append(f"| {i['nome']} | {celula(i['descricao'])} | `{celula(i['formula'])}` | {fonte} | {valor} |")
            linhas.append("")
    return "\n".join(linhas).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--servidor", default=r"localhost\SQLEXPRESS")
    parser.add_argument("--pasta", type=Path, default=PASTA_PADRAO)
    args = parser.parse_args()

    conexao = conectar(args.servidor, BANCO, escolher_driver())
    catalogo = montar(conexao.cursor())
    conexao.close()

    DOC.write_text(escrever_markdown(catalogo), encoding="utf-8")
    saida = args.pasta / "indicadores.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ind = catalogo["indicadores"]
    print(f"{len(ind)} indicadores, {sum(1 for i in ind if i['conferido'])} conferidos com o SQL, "
          f"{len(catalogo['homonimos'])} nomes repetidos entre modelos")
    print(f"  gravado {DOC}")
    print(f"  gravado {saida} ({saida.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
