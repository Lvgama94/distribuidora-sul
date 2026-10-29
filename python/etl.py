"""
ETL da Distribuidora Sul: lê os arquivos brutos dos sistemas de origem, corrige
os problemas de qualidade e grava arquivos padronizados em data/tratado/
(UTF-8, separador vírgula, ponto decimal e datas ISO).

Cada correção é contada e registrada em docs/relatorio_qualidade.md, para
deixar claro o que foi encontrado em cada fonte e o que foi feito.

Uso:   python python/etl.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BRUTO = RAIZ / "data" / "bruto"
TRATADO = RAIZ / "data" / "tratado"
DATA_CORTE = pd.Timestamp("2025-12-31")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
class Relatorio:
    def __init__(self):
        self.secoes: dict[str, list[tuple[str, int, str]]] = {}
        self.saidas: list[tuple[str, int]] = []

    def registrar(self, fonte: str, verificacao: str, ocorrencias: int, acao: str):
        self.secoes.setdefault(fonte, []).append((verificacao, int(ocorrencias), acao))

    def salvar(self, caminho: Path):
        linhas = ["# Relatório de qualidade dos dados", "",
                  "Gerado automaticamente por `python/etl.py` a cada execução.", ""]
        for fonte, itens in self.secoes.items():
            linhas += [f"## {fonte}", "", "| Verificação | Ocorrências | O que foi feito |", "|---|---:|---|"]
            linhas += [f"| {v} | {milhar(n)} | {a} |" for v, n, a in itens]
            linhas.append("")
        linhas += ["## Arquivos gerados em `data/tratado/`", "", "| Arquivo | Linhas |", "|---|---:|"]
        linhas += [f"| `{nome}.csv` | {milhar(n)} |" for nome, n in self.saidas]
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


rel = Relatorio()


def chave(texto) -> str:
    """Texto sem acento, minúsculo e sem espaços extras, para comparar variações de digitação."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def numero_br(serie: pd.Series) -> pd.Series:
    """Converte '1.234,56' ou 'R$ 1.234,56' em número."""
    s = serie.astype("string").str.replace("R$", "", regex=False).str.strip()
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def data_br(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")


def somente_digitos(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.replace(r"\D", "", regex=True)


def cnpj_valido(cnpj: str) -> bool:
    if not isinstance(cnpj, str) or len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    numeros = [int(c) for c in cnpj]
    for tamanho, pesos in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]), (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        resto = sum(d * p for d, p in zip(numeros[:tamanho], pesos)) % 11
        if numeros[tamanho] != (0 if resto < 2 else 11 - resto):
            return False
    return True


def ler_csv(caminho: str, encoding: str = "cp1252") -> pd.DataFrame:
    return pd.read_csv(BRUTO / caminho, sep=";", encoding=encoding, dtype=str, keep_default_na=False,
                       na_values=[""])


def salvar(df: pd.DataFrame, nome: str):
    df.to_csv(TRATADO / f"{nome}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d")
    rel.saidas.append((nome, len(df)))


MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}
SIGLAS = {"me", "eireli", "s.a.", "rs"}


def nome_proprio(texto: str) -> str:
    palavras = []
    for i, p in enumerate(texto.lower().split()):
        if p in SIGLAS:
            palavras.append(p.upper())
        elif p in MINUSCULAS and i > 0:
            palavras.append(p)
        else:
            palavras.append(p[:1].upper() + p[1:])
    return " ".join(palavras)


# ---------------------------------------------------------------------------
# Cadastros
# ---------------------------------------------------------------------------
def tratar_cadastros():
    filiais = ler_csv("cadastros/filiais.csv", "utf-8-sig")
    centros = ler_csv("cadastros/centros_custo.csv", "utf-8-sig")
    contas = ler_csv("cadastros/plano_contas.csv", "utf-8-sig")
    salvar(filiais, "filial")
    salvar(centros, "centro_custo")
    salvar(contas, "conta")
    return filiais, centros


CATEGORIAS = {"bebidas": "Bebidas", "bebida": "Bebidas", "mercearia": "Mercearia", "laticinios": "Laticínios",
              "limpeza": "Limpeza", "higiene": "Higiene", "higiene pessoal": "Higiene",
              "congelados": "Congelados", "congelado": "Congelados"}


def tratar_produtos():
    p = pd.read_excel(BRUTO / "compras/cadastro_produtos.xlsx", dtype=str)
    p.columns = ["cod_produto", "descricao", "categoria", "unidade", "cod_fornecedor", "preco_tabela_jan2024",
                 "ativo"]
    categoria = p.categoria.map(lambda c: CATEGORIAS.get(chave(c)))
    rel.registrar("Cadastro de produtos (Excel de compras)", "Categoria escrita de formas diferentes "
                  "(ex.: BEBIDAS, bebida, Laticinios)", (categoria != p.categoria).sum(),
                  "Padronizada para as 6 categorias oficiais")
    rel.registrar("Cadastro de produtos (Excel de compras)", "Categoria não reconhecida", categoria.isna().sum(),
                  "Revisar manualmente")
    p["categoria"] = categoria
    p["preco_tabela_jan2024"] = pd.to_numeric(p.preco_tabela_jan2024)
    salvar(p, "produto")
    return p


def tratar_fornecedores():
    f = ler_csv("erp/fornecedores.csv")
    mascarado = f.cnpj.str.contains(r"\D", na=False)
    f["cnpj"] = somente_digitos(f.cnpj)
    rel.registrar("Fornecedores (ERP)", "CNPJ com máscara (pontos, barra e traço)", mascarado.sum(),
                  "Mantidos só os 14 dígitos")
    rel.registrar("Fornecedores (ERP)", "CNPJ com dígito verificador inválido", (~f.cnpj.map(cnpj_valido)).sum(),
                  "Nenhuma ação (todos válidos)")
    for col in ("prazo_pagamento_dias", "lead_time_dias"):
        f[col] = pd.to_numeric(f[col]).astype("Int64")
    salvar(f, "fornecedor")
    return f


APELIDOS_CIDADE = {"poa": "porto alegre", "caxias": "caxias do sul"}


def tratar_clientes():
    c = ler_csv("erp/clientes.csv")
    fonte = "Clientes (ERP)"

    razao = c.razao_social
    espacos = (razao != razao.str.strip()) | razao.str.contains(r"\s{2,}", na=False)
    razao = razao.str.strip().str.replace(r"\s+", " ", regex=True)
    caixa_alta = razao == razao.str.upper()
    c["razao_social"] = razao.mask(caixa_alta, razao.map(nome_proprio))
    rel.registrar(fonte, "Razão social com espaços sobrando", espacos.sum(), "Espaços removidos")
    rel.registrar(fonte, "Razão social toda em maiúsculas", caixa_alta.sum(), "Convertida para nome próprio")

    k = c.cidade.map(chave)
    apelido = k.isin(list(APELIDOS_CIDADE))
    k = k.replace(APELIDOS_CIDADE)
    grafia = c[~apelido].groupby(k[~apelido]).cidade.agg(lambda s: s.value_counts().index[0])
    cidade = k.map(grafia)
    rel.registrar(fonte, "Cidade com grafia diferente (ex.: POA, Porto alegre, Sao Leopoldo)",
                  (cidade != c.cidade).sum(), "Padronizada pela grafia mais usada de cada cidade")
    c["cidade"] = cidade

    mascarado = c.cnpj.str.contains(r"\D", na=False)
    c["cnpj"] = somente_digitos(c.cnpj)
    rel.registrar(fonte, "CNPJ com máscara", mascarado.sum(), "Mantidos só os 14 dígitos")
    rel.registrar(fonte, "CNPJ com dígito verificador inválido", (~c.cnpj.map(cnpj_valido)).sum(),
                  "Nenhuma ação (todos válidos)")

    c["data_cadastro"] = data_br(c.data_cadastro)
    c["limite_credito"] = numero_br(c.limite_credito)
    c["id_filial"] = c.id_filial.astype(int)

    # Mesmo CNPJ com dois códigos: o código mais antigo vira o mestre
    c = c.sort_values(["cnpj", "data_cadastro"])
    c["cod_mestre"] = c.groupby("cnpj").cod_cliente.transform("first")
    duplicados = c[c.cod_cliente != c.cod_mestre]
    de_para = duplicados[["cod_cliente", "cod_mestre"]].rename(columns={"cod_cliente": "cod_cliente_duplicado"})
    rel.registrar(fonte, "Cliente cadastrado duas vezes (mesmo CNPJ, códigos diferentes)", len(duplicados),
                  "Unificado no código mais antigo; tabela de-para aplicada em vendas e contas a receber")
    c = c[c.cod_cliente == c.cod_mestre].drop(columns="cod_mestre").sort_values("cod_cliente")
    salvar(c, "cliente")
    salvar(de_para, "de_para_cliente")
    return c, dict(zip(de_para.cod_cliente_duplicado, de_para.cod_mestre))


# ---------------------------------------------------------------------------
# Operação
# ---------------------------------------------------------------------------
def tratar_vendas(produtos: pd.DataFrame, mapa_clientes: dict):
    v = ler_csv("erp/vendas_itens.csv")
    fonte = "Vendas - itens de nota fiscal (ERP)"

    antes = len(v)
    v = v.drop_duplicates()
    rel.registrar(fonte, "Linha exportada em duplicidade (idêntica a outra)", antes - len(v), "Removida")

    cod = v.cod_produto.str.strip().str.upper()
    rel.registrar(fonte, "Código de produto com espaço ou minúscula (ex.: ' p0012')", (cod != v.cod_produto).sum(),
                  "Padronizado")
    v["cod_produto"] = cod
    rel.registrar(fonte, "Produto inexistente no cadastro", (~v.cod_produto.isin(produtos.cod_produto)).sum(),
                  "Nenhum após a padronização")

    trocados = v.cod_cliente.isin(list(mapa_clientes))
    v["cod_cliente"] = v.cod_cliente.replace(mapa_clientes)
    rel.registrar(fonte, "Venda lançada no código duplicado do cliente", trocados.sum(), "Apontada para o código mestre")

    v["data_emissao"] = data_br(v.data_emissao)
    for col in ("serie", "nf_numero", "qtd_pedida", "qtd_faturada"):
        v[col] = v[col].astype(int)
    v["nf_referencia"] = pd.to_numeric(v.nf_referencia).astype("Int64")
    v["preco_unitario"] = numero_br(v.preco_unitario)
    v["desconto_pct"] = numero_br(v.desconto_pct)
    v["custo_medio_unitario"] = numero_br(v.custo_medio_unitario)

    mediana = v.groupby(["cod_produto", v.data_emissao.dt.to_period("M")]).preco_unitario.transform("median")
    fora = v.preco_unitario > mediana * 20
    rel.registrar(fonte, "Preço unitário 100 vezes maior que o normal (vírgula esquecida na digitação)", fora.sum(),
                  "Dividido por 100")
    v.loc[fora, "preco_unitario"] = (v.loc[fora, "preco_unitario"] / 100).round(2)

    chave_nf = v.duplicated(["serie", "nf_numero", "cod_produto"])
    rel.registrar(fonte, "Item repetido na mesma nota (série + nota + produto)", chave_nf.sum(),
                  "Nenhum após remover as duplicidades")
    rel.registrar(fonte, "Notas canceladas", v[v.status == "CANCELADO"].drop_duplicates(["serie", "nf_numero"]).shape[0],
                  "Mantidas com status; o modelo filtra na carga")
    salvar(v, "venda_item")


def tratar_compras():
    c = ler_csv("erp/pedidos_compra.csv")
    for col in ("data_pedido", "data_entrega_prevista", "data_entrega_real"):
        c[col] = data_br(c[col])
    c["quantidade"] = c.quantidade.astype(int)
    c["custo_unitario"] = numero_br(c.custo_unitario)
    rel.registrar("Pedidos de compra (ERP)", "Pedido ainda não entregue na data de corte",
                  c[c.status == "EM ABERTO"].pedido_numero.nunique(), "Mantido sem data de entrega real")
    salvar(c, "pedido_compra_item")

    e = ler_csv("erp/estoque_inicial.csv")
    e["quantidade"] = e.quantidade.astype(int)
    e["custo_medio"] = numero_br(e.custo_medio)
    e["data_posicao"] = data_br(e.data_posicao)
    salvar(e, "estoque_inicial")


# ---------------------------------------------------------------------------
# Financeiro
# ---------------------------------------------------------------------------
def tratar_receber(mapa_clientes: dict):
    r = ler_csv("financeiro/contas_receber.csv")
    fonte = "Contas a receber (financeiro)"
    for col in ("data_emissao", "data_vencimento", "data_pagamento"):
        r[col] = data_br(r[col])
    r["valor"] = numero_br(r.valor)
    r["valor_pago"] = numero_br(r.valor_pago)
    r["serie"] = r.serie.astype(int)
    r["nf_numero"] = r.nf_numero.astype(int)

    erro = r.data_pagamento < r.data_emissao
    corrigida = r.data_pagamento + pd.DateOffset(years=1)
    ano_errado = erro & (corrigida >= r.data_emissao) & (corrigida <= DATA_CORTE)
    rel.registrar(fonte, "Pagamento com data anterior à emissão (ano digitado errado na baixa)", ano_errado.sum(),
                  "Ano corrigido (+1) quando a nova data fica entre a emissão e a data de corte")
    r.loc[ano_errado, "data_pagamento"] = corrigida[ano_errado]
    sem_conserto = erro & ~ano_errado
    rel.registrar(fonte, "Pagamento anterior à emissão sem correção possível", sem_conserto.sum(),
                  "Data apagada para revisão do financeiro")
    r.loc[sem_conserto, "data_pagamento"] = pd.NaT

    trocados = r.cod_cliente.isin(list(mapa_clientes))
    r["cod_cliente"] = r.cod_cliente.replace(mapa_clientes)
    rel.registrar(fonte, "Título no código duplicado do cliente", trocados.sum(), "Apontado para o código mestre")
    salvar(r, "conta_receber")


def data_mista(serie: pd.Series) -> tuple[pd.Series, int]:
    """Aceita dd/mm/aaaa e aaaa-mm-dd na mesma coluna."""
    iso = serie.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    resultado = pd.to_datetime(serie.where(~iso), format="%d/%m/%Y", errors="coerce")
    resultado[iso] = pd.to_datetime(serie[iso], format="%Y-%m-%d")
    return resultado, int(iso.sum())


def tratar_pagar(fornecedores: pd.DataFrame, centros: pd.DataFrame):
    p = ler_csv("financeiro/contas_pagar.csv")
    fonte = "Contas a pagar (planilha do financeiro)"
    p.columns = ["id_titulo", "fornecedor", "cnpj", "documento", "descricao", "cod_conta", "cod_centro_custo",
                 "id_filial", "competencia", "data_emissao", "data_vencimento", "data_pagamento", "valor",
                 "valor_pago"]

    linhas_iso = 0
    for col in ("data_emissao", "data_vencimento", "data_pagamento"):
        p[col], n = data_mista(p[col])
        linhas_iso += n
    rel.registrar(fonte, "Datas em formato aaaa-mm-dd misturadas com dd/mm/aaaa", linhas_iso,
                  "Lidas nos dois formatos")
    rel.registrar(fonte, "Valores como texto 'R$ 1.234,56'", p.valor.notna().sum(), "Convertidos para número")
    p["valor"] = numero_br(p.valor)
    p["valor_pago"] = numero_br(p.valor_pago)
    p["competencia"] = pd.to_datetime("01/" + p.competencia, format="%d/%m/%Y")
    p["id_titulo"] = p.id_titulo.astype(int)
    p["id_filial"] = p.id_filial.astype(int)

    p["cnpj"] = somente_digitos(p.cnpj)
    p = p.merge(fornecedores[["cnpj", "cod_fornecedor"]], on="cnpj", how="left")
    rel.registrar(fonte, "Fornecedor sem cadastro (CNPJ não encontrado)", p.cod_fornecedor.isna().sum(),
                  "Nenhum: todos ligados ao cadastro pelo CNPJ")

    vazio = p.cod_centro_custo.isna()
    nomes = {chave(nome): cod for cod, nome in zip(centros.cod_centro_custo, centros.nome)}

    def cc_pela_descricao(descricao: str):
        texto = chave(descricao)
        return next((cod for nome, cod in nomes.items() if nome in texto), None)

    pela_descricao = p.loc[vazio, "descricao"].map(cc_pela_descricao)
    p.loc[vazio, "cod_centro_custo"] = pela_descricao
    moda = p[~vazio].groupby("cod_conta").cod_centro_custo.agg(lambda s: s.mode().iloc[0])
    ainda_vazio = p.cod_centro_custo.isna()
    p.loc[ainda_vazio, "cod_centro_custo"] = p.loc[ainda_vazio, "cod_conta"].map(moda)
    rel.registrar(fonte, "Centro de custo em branco", vazio.sum(),
                  f"{pela_descricao.notna().sum()} preenchidos pelo setor citado na descrição e "
                  f"{ainda_vazio.sum()} pelo centro de custo mais usado na mesma conta")

    p = p.drop(columns=["fornecedor", "cnpj"])
    salvar(p, "conta_pagar")


MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def tratar_orcamento():
    fonte = "Orçamento (Excel da controladoria)"
    arquivo = pd.ExcelFile(BRUTO / "financeiro/orcamento.xlsx")
    partes = []
    for aba in arquivo.sheet_names:
        ano = int(aba[-4:])
        o = pd.read_excel(arquivo, aba, header=3, dtype={"Conta": str, "Centro de custo": str})
        divergente = (o[MESES].sum(axis=1) - o.Total).abs() > 0.01
        rel.registrar(fonte, f"{aba}: linhas cujo total não bate com a soma dos meses", divergente.sum(),
                      "Conferido; a coluna Total é descartada")
        longo = o.melt(id_vars=["Conta", "Centro de custo"], value_vars=MESES, var_name="mes", value_name="valor")
        longo["competencia"] = pd.to_datetime({"year": ano, "month": longo.mes.map(MESES.index) + 1, "day": 1})
        partes.append(longo)
    rel.registrar(fonte, "Formato largo (um mês por coluna) com 3 linhas de título", len(arquivo.sheet_names),
                  "Títulos ignorados e meses transformados em linhas")
    o = pd.concat(partes).rename(columns={"Conta": "cod_conta", "Centro de custo": "cod_centro_custo"})
    salvar(o[["competencia", "cod_conta", "cod_centro_custo", "valor"]], "orcamento")


# ---------------------------------------------------------------------------
# RH
# ---------------------------------------------------------------------------
SETORES = {"diretoria": "CC01", "comercial": "CC02", "vendas": "CC02", "logistica": "CC03", "financeiro": "CC04",
           "recursos humanos": "CC05", "compras": "CC06", "tecnologia da informacao": "CC07",
           "administrativo": "CC08", "adm": "CC08"}


def tratar_funcionarios(filiais: pd.DataFrame, centros: pd.DataFrame):
    f = pd.read_excel(BRUTO / "rh/funcionarios.xlsx", dtype={"Matrícula": str})
    fonte = "Quadro de funcionários (Excel do RH)"
    f.columns = ["matricula", "nome", "sexo", "data_nascimento", "cargo", "setor", "filial", "data_admissao",
                 "data_desligamento", "motivo_desligamento", "salario_atual"]
    rel.registrar(fonte, "Salário como texto 'R$ 2.350,00'", len(f), "Convertido para número")
    f["salario_atual"] = numero_br(f.salario_atual)
    cc = f.setor.map(lambda s: SETORES.get(chave(s)))
    nome_oficial = cc.map(dict(zip(centros.cod_centro_custo, centros.nome)))
    rel.registrar(fonte, "Setor escrito de formas diferentes (ex.: Logistica, Adm, Vendas)",
                  (f.setor != nome_oficial).sum(), "Ligado ao código do centro de custo")
    rel.registrar(fonte, "Setor não reconhecido", cc.isna().sum(), "Revisar manualmente")
    f["cod_centro_custo"] = cc
    f["id_filial"] = f.filial.map(dict(zip(filiais.nome, filiais.id_filial.astype(int))))
    rel.registrar(fonte, "Data de nascimento em branco", f.data_nascimento.isna().sum(),
                  "Mantida em branco (não dá para inventar); a faixa etária fica 'Não informada'")
    for col in ("data_nascimento", "data_admissao", "data_desligamento"):
        f[col] = pd.to_datetime(f[col])
    f["motivo_desligamento"] = f.motivo_desligamento.fillna("")
    salvar(f.drop(columns=["setor", "filial"]), "funcionario")


LAYOUT_NOVO = {"Matrícula": "matricula", "Nome do colaborador": "nome", "Setor": "setor",
               "HE (hh:mm)": "horas_extras", "Faltas": "faltas", "Atestados (dias)": "atestado_dias",
               "Dias trab.": "dias_trabalhados"}


def tratar_ponto():
    fonte = "Ponto mensal (um CSV por mês do RH)"
    partes, novos = [], 0
    arquivos = sorted((BRUTO / "rh" / "ponto").glob("ponto_*.csv"))
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig", dtype=str)
        if "Matrícula" in df.columns:
            df = df.rename(columns=LAYOUT_NOVO)
            novos += 1
        ano, mes = map(int, re.findall(r"\d+", arquivo.stem))
        df["competencia"] = pd.Timestamp(ano, mes, 1)
        partes.append(df)
    rel.registrar(fonte, "Arquivos mensais para consolidar", len(arquivos), "Empilhados em uma tabela só")
    rel.registrar(fonte, "Arquivos com o layout novo (colunas renomeadas e em outra ordem a partir de mar/2025)",
                  novos, "Colunas mapeadas para o layout padrão")
    p = pd.concat(partes, ignore_index=True)
    horas = p.horas_extras.str.split(":", expand=True).astype(int)
    p["horas_extras"] = (horas[0] + horas[1] / 60).round(2)
    rel.registrar(fonte, "Horas extras em texto hh:mm", len(p), "Convertidas para horas decimais (ex.: 12:30 = 12,5)")
    for col in ("dias_trabalhados", "faltas", "atestado_dias"):
        p[col] = p[col].astype(int)
    p["cod_centro_custo"] = p.setor.map(lambda s: SETORES.get(chave(s)))
    salvar(p[["competencia", "matricula", "cod_centro_custo", "dias_trabalhados", "faltas", "atestado_dias",
              "horas_extras"]], "ponto_mensal")


def main():
    TRATADO.mkdir(parents=True, exist_ok=True)
    filiais, centros = tratar_cadastros()
    produtos = tratar_produtos()
    fornecedores = tratar_fornecedores()
    _, mapa_clientes = tratar_clientes()
    tratar_vendas(produtos, mapa_clientes)
    tratar_compras()
    tratar_receber(mapa_clientes)
    tratar_pagar(fornecedores, centros)
    tratar_orcamento()
    tratar_funcionarios(filiais, centros)
    tratar_ponto()
    rel.salvar(RAIZ / "docs" / "relatorio_qualidade.md")
    for nome, n in rel.saidas:
        print(f"  {nome:<20} {n:>8,} linhas")
    print("Relatório: docs/relatorio_qualidade.md")


if __name__ == "__main__":
    main()
