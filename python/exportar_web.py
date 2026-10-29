"""
Exporta os dados dos painéis para a versão web interativa do portfólio.

Para cada painel (Financeiro, People Analytics, Compras e Estoque), resume as
fatos por mês e pelas dimensões dos filtros e grava um JSON pequeno que o site
lê no navegador. Antes de gravar, recalcula a partir do próprio JSON os
indicadores da view de conferência do painel (dw.vw_conferencia_*) e para se
algum não bater com o SQL. O painel "excel" lê as tabelas que o Power Query
gravou nas pastas de trabalho de excel/ e as confere com o SQL e o CSV do banco.

Uso:   python python/exportar_web.py                 (os quatro painéis)
       python python/exportar_web.py --painel rh
       python python/exportar_web.py --pasta ../portfolio/assets/data
Requer o banco DistribuidoraSul carregado (python/carregar_sql.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl

from carregar_sql import BANCO, RAIZ, conectar, escolher_driver

PASTA_PADRAO = RAIZ.parent / "portfolio" / "assets" / "data"
FAIXAS = ["A vencer", "1 a 30 dias", "31 a 60 dias", "61 a 90 dias", "Mais de 90 dias"]


def consultar(cursor, sql: str):
    return [tuple(linha) for linha in cursor.execute(sql).fetchall()]


def mes(chave: int) -> str:
    """20250301 -> '2025-03'"""
    return f"{chave // 10000}-{chave // 100 % 100:02d}"


def reais(valor) -> float:
    return round(float(valor), 2)


# ------------------------------------------------------------ Financeiro

def exportar_financeiro(cursor) -> dict:
    contas = consultar(cursor, """
        SELECT cod_conta, descricao, grupo_dre, ordem_grupo, sinal
        FROM dw.dim_conta WHERE entra_dre = 1 ORDER BY cod_conta""")
    filiais = consultar(cursor, "SELECT filial_key, cidade FROM dw.dim_filial ORDER BY filial_key")
    indice_conta = {cod: i for i, (cod, *_) in enumerate(contas)}

    dre = consultar(cursor, """
        SELECT d.competencia_key, d.filial_key, c.cod_conta, SUM(d.valor)
        FROM dw.fato_dre d JOIN dw.dim_conta c ON c.conta_key = d.conta_key
        GROUP BY d.competencia_key, d.filial_key, c.cod_conta""")
    orcamento = consultar(cursor, """
        SELECT o.competencia_key, c.cod_conta, SUM(o.valor)
        FROM dw.fato_orcamento o JOIN dw.dim_conta c ON c.conta_key = o.conta_key
        GROUP BY o.competencia_key, c.cod_conta""")
    # Caixa pela data de pagamento; prazos ponderados pelo valor do título
    recebido = consultar(cursor, """
        SELECT pagamento_key / 100 * 100 + 1, filial_key, SUM(valor_pago), SUM(valor),
               SUM(valor * prazo_real_dias), SUM(valor * prazo_concedido_dias)
        FROM dw.fato_conta_receber WHERE pagamento_key IS NOT NULL
        GROUP BY pagamento_key / 100 * 100 + 1, filial_key""")
    pago = consultar(cursor, """
        SELECT p.pagamento_key / 100 * 100 + 1, p.filial_key, c.grupo_caixa, SUM(p.valor_pago),
               SUM(CASE WHEN c.cod_conta = '1.05' THEN p.valor END),
               SUM(CASE WHEN c.cod_conta = '1.05' THEN p.valor * p.prazo_real_dias END)
        FROM dw.fato_conta_pagar p JOIN dw.dim_conta c ON c.conta_key = p.conta_key
        WHERE p.pagamento_key IS NOT NULL
        GROUP BY p.pagamento_key / 100 * 100 + 1, p.filial_key, c.grupo_caixa""")
    # Carteira: fotografia dos títulos em aberto na data de corte
    carteira = consultar(cursor, """
        SELECT r.filial_key, cli.tipo_cliente, r.faixa_aging, SUM(r.valor)
        FROM dw.fato_conta_receber r JOIN dw.dim_cliente cli ON cli.cliente_key = r.cliente_key
        WHERE r.status <> 'PAGO'
        GROUP BY r.filial_key, cli.tipo_cliente, r.faixa_aging""")

    chaves = {k for k, *_ in dre} | {k for k, *_ in orcamento} | {k for k, *_ in recebido} | {k for k, *_ in pago}
    meses = sorted({mes(k) for k in chaves})
    indice_mes = {m: i for i, m in enumerate(meses)}
    grupos_caixa = sorted({g for _, _, g, *_ in pago})
    tipos = sorted({t for _, t, _, _ in carteira})

    return {
        "gerado_em": date.today().isoformat(),
        "data_corte": "2025-12-31",
        "meses": meses,
        "filiais": [{"id": f, "nome": nome} for f, nome in filiais],
        "contas": [{"cod": cod, "nome": nome, "grupo": grupo, "ordem": ordem, "sinal": sinal}
                   for cod, nome, grupo, ordem, sinal in contas],
        "grupos_caixa": grupos_caixa,
        "tipos_cliente": tipos,
        "faixas_aging": FAIXAS,
        # [mês, filial, conta, valor positivo da conta]
        "dre": [[indice_mes[mes(k)], f, indice_conta[cod], reais(v)] for k, f, cod, v in dre],
        # [mês, conta, valor] (o orçamento não é aberto por filial)
        "orcamento": [[indice_mes[mes(k)], indice_conta[cod], reais(v)] for k, cod, v in orcamento],
        # [mês, filial, recebido, valor dos títulos, valor × prazo real, valor × prazo concedido]
        "recebido": [[indice_mes[mes(k)], f, reais(rec), reais(val), reais(vp), reais(vc)]
                     for k, f, rec, val, vp, vc in recebido],
        # [mês, filial, grupo de caixa, pago, valor das compras de mercadoria, valor × prazo real]
        "pago": [[indice_mes[mes(k)], f, grupos_caixa.index(g), reais(p), reais(v or 0), reais(vp or 0)]
                 for k, f, g, p, v, vp in pago],
        # [filial, tipo de cliente, faixa de aging, valor em aberto]
        "carteira": [[f, tipos.index(t), FAIXAS.index(faixa), reais(v)] for f, t, faixa, v in carteira],
    }


def indicadores_financeiro(dados: dict) -> dict:
    """Recalcula, só com o JSON, os indicadores de dw.vw_conferencia_financeiro (todas as filiais)."""
    contas, meses = dados["contas"], dados["meses"]
    ano = lambda i: int(meses[i][:4])
    soma = defaultdict(float)
    for m, _, c, v in dados["dre"]:
        a, conta = ano(m), contas[c]
        soma[a, "resultado"] += v * conta["sinal"]
        if conta["cod"] == "3.01":
            soma[a, "bruta"] += v
        elif conta["grupo"] == "Deduções da receita":
            soma[a, "deducoes"] += v
        elif conta["grupo"] == "CMV":
            soma[a, "cmv"] += v
        elif 4 <= conta["ordem"] <= 7:
            soma[a, "despesas"] += v
    for m, c, v in dados["orcamento"]:
        soma[ano(m), "resultado_orcado"] += v * contas[c]["sinal"]
        if contas[c]["cod"] == "3.01":
            soma[ano(m), "receita_orcada"] += v
    for m, _, rec, val, vp, vc in dados["recebido"]:
        for nome, x in (("recebido", rec), ("rec_valor", val), ("rec_vp", vp), ("rec_vc", vc)):
            soma[ano(m), nome] += x
    for m, _, _, p, v, vp in dados["pago"]:
        for nome, x in (("pago", p), ("pag_valor", v), ("pag_vp", vp)):
            soma[ano(m), nome] += x

    resultado = {}
    for a in sorted({a for a, _ in soma}):
        s = lambda nome: soma[a, nome]
        liquida = s("bruta") - s("deducoes")
        resultado.update({
            (a, "Receita Bruta"): s("bruta"),
            (a, "Receita Líquida"): liquida,
            (a, "CMV"): s("cmv"),
            (a, "Lucro Bruto"): liquida - s("cmv"),
            (a, "Margem Bruta %"): (liquida - s("cmv")) / liquida,
            (a, "Despesas Operacionais"): s("despesas"),
            (a, "Resultado Líquido"): s("resultado"),
            (a, "Margem Líquida %"): s("resultado") / liquida,
            (a, "Receita Orçada"): s("receita_orcada"),
            (a, "Atingimento da Receita %"): s("bruta") / s("receita_orcada"),
            (a, "Resultado Orçado"): s("resultado_orcado"),
            (a, "Desvio do Resultado"): s("resultado") - s("resultado_orcado"),
            (a, "Recebido"): s("recebido"),
            (a, "Pago"): s("pago"),
            (a, "Geração de Caixa"): s("recebido") - s("pago"),
            (a, "PMR (dias)"): s("rec_vp") / s("rec_valor"),
            (a, "Prazo Médio Concedido (dias)"): s("rec_vc") / s("rec_valor"),
            (a, "PMP (dias)"): s("pag_vp") / s("pag_valor"),
        })

    vencida = lambda faixa: dados["faixas_aging"][faixa] != "A vencer"
    carteira = sum(v for *_, v in dados["carteira"])
    vencido = sum(v for _, _, faixa, v in dados["carteira"] if vencida(faixa))
    acima_90 = sum(v for _, _, faixa, v in dados["carteira"] if dados["faixas_aging"][faixa] == "Mais de 90 dias")
    resultado.update({
        (None, "Carteira em Aberto"): carteira,
        (None, "Vencido"): vencido,
        (None, "Vencido há Mais de 90 Dias"): acima_90,
        (None, "Inadimplência %"): vencido / carteira,
    })
    return resultado


# ------------------------------------------------------------ People Analytics

def exportar_rh(cursor) -> dict:
    setores = consultar(cursor, "SELECT cc_key, nome FROM dw.dim_centro_custo ORDER BY cc_key")
    filiais = consultar(cursor, "SELECT filial_key, cidade FROM dw.dim_filial ORDER BY filial_key")
    indice_setor = {k: i for i, (k, _) in enumerate(setores)}
    # Setor, filial e cargo são os do mês, como no Power BI (a fato traz o setor da época)
    quadro = consultar(cursor, """
        SELECT q.competencia_key, q.cc_key, q.filial_key, f.cargo,
               SUM(CAST(q.ativo_inicio_mes AS INT)), SUM(CAST(q.ativo_fim_mes AS INT)),
               SUM(CAST(q.admitido_no_mes AS INT)), SUM(CAST(q.desligado_no_mes AS INT)),
               SUM(CAST(q.desligamento_voluntario AS INT))
        FROM dw.fato_quadro_mensal q JOIN dw.dim_funcionario f ON f.funcionario_key = q.funcionario_key
        GROUP BY q.competencia_key, q.cc_key, q.filial_key, f.cargo""")
    desligados = consultar(cursor, """
        SELECT q.competencia_key, q.cc_key, q.filial_key, f.cargo, f.faixa_tempo_casa,
               f.motivo_desligamento, f.tipo_desligamento, f.tempo_casa_meses
        FROM dw.fato_quadro_mensal q JOIN dw.dim_funcionario f ON f.funcionario_key = q.funcionario_key
        WHERE q.desligado_no_mes = 1""")
    # "Quem saiu × quem ficou" usa a situação atual do funcionário, como a medida DAX
    ponto = consultar(cursor, """
        SELECT p.competencia_key, p.cc_key, p.filial_key, 1 - CAST(f.ativo AS INT),
               SUM(p.dias_previstos), SUM(p.faltas), SUM(p.atestado_dias), SUM(p.horas_extras), COUNT(*)
        FROM dw.fato_ponto p JOIN dw.dim_funcionario f ON f.funcionario_key = p.funcionario_key
        GROUP BY p.competencia_key, p.cc_key, p.filial_key, f.ativo""")
    custo = consultar(cursor, """
        SELECT competencia_key, cc_key, filial_key, SUM(valor) FROM dw.vw_custo_pessoal
        GROUP BY competencia_key, cc_key, filial_key""")

    meses = sorted({mes(k) for k, *_ in quadro} | {mes(k) for k, *_ in ponto} | {mes(k) for k, *_ in custo})
    indice_mes = {m: i for i, m in enumerate(meses)}
    cargos = sorted({c for _, _, _, c, *_ in quadro})
    faixas = ["Até 3 meses", "3 a 12 meses", "1 a 2 anos", "2 a 5 anos", "Mais de 5 anos"]
    motivos = sorted({m for *_, m, _, _ in desligados})
    return {
        "gerado_em": date.today().isoformat(),
        "meses": meses,
        "setores": [nome for _, nome in setores],
        "filiais": [{"id": f, "nome": nome} for f, nome in filiais],
        "cargos": cargos,
        "faixas_tempo_casa": faixas,
        "motivos": [{"nome": m, "voluntario": next(t for *_, mo, t, _ in desligados if mo == m) == "Voluntário"} for m in motivos],
        # [mês, setor, filial, cargo, ativos no início, ativos no fim, admissões, desligamentos, voluntários]
        "quadro": [[indice_mes[mes(k)], indice_setor[cc], f, cargos.index(c), *map(int, x)] for k, cc, f, c, *x in quadro],
        # [mês, setor, filial, cargo, faixa de tempo de casa, motivo, voluntário (0/1), tempo de casa em meses]
        "desligados": [[indice_mes[mes(k)], indice_setor[cc], f, cargos.index(c), faixas.index(fx), motivos.index(mo),
                        int(t == "Voluntário"), int(tc)] for k, cc, f, c, fx, mo, t, tc in desligados],
        # [mês, setor, filial, saiu (0/1), dias previstos, faltas, dias de atestado, horas extras, pessoas no mês]
        "ponto": [[indice_mes[mes(k)], indice_setor[cc], f, int(s), int(dp), int(fa), int(at), reais(he), int(n)]
                  for k, cc, f, s, dp, fa, at, he, n in ponto],
        # [mês, setor, filial, custo de pessoal (salários + encargos + benefícios)]
        "custo": [[indice_mes[mes(k)], indice_setor[cc], f, reais(v)] for k, cc, f, v in custo],
    }


def indicadores_rh(dados: dict) -> dict:
    """Recalcula, só com o JSON, os indicadores de dw.vw_conferencia_rh (empresa toda)."""
    ano = lambda i: int(dados["meses"][i][:4])
    mensal = defaultdict(lambda: [0] * 5)          # (ano, mês) -> início, fim, admissões, desligamentos, voluntários
    for m, _, _, _, *x in dados["quadro"]:
        mensal[ano(m), m] = [a + b for a, b in zip(mensal[ano(m), m], x)]
    soma = defaultdict(float)
    for d in dados["desligados"]:
        soma[ano(d[0]), "experiencia"] += d[7] < 3
    for m, _, _, _, dp, fa, at, he, _ in dados["ponto"]:
        soma[ano(m), "previstos"] += dp; soma[ano(m), "ausencias"] += fa + at; soma[ano(m), "he"] += he
    for m, _, _, v in dados["custo"]:
        soma[ano(m), "custo"] += v

    resultado = {}
    for a in sorted({a for a, _ in mensal}):
        meses_ano = [v for (aa, _), v in sorted(mensal.items()) if aa == a]
        medio = sum((v[0] + v[1]) / 2 for v in meses_ano) / len(meses_ano)
        desl, vol = sum(v[3] for v in meses_ano), sum(v[4] for v in meses_ano)
        resultado.update({
            (a, "Headcount"): meses_ano[-1][1],
            (a, "Headcount Médio"): medio,
            (a, "Admissões"): sum(v[2] for v in meses_ano),
            (a, "Desligamentos"): desl,
            (a, "Turnover %"): desl / medio,
            (a, "Turnover Voluntário %"): vol / medio,
            (a, "Desligamentos na Experiência"): soma[a, "experiencia"],
            (a, "Absenteísmo %"): soma[a, "ausencias"] / soma[a, "previstos"],
            (a, "Horas Extras"): soma[a, "he"],
            (a, "Custo de Pessoal"): soma[a, "custo"],
        })
    return resultado


# ------------------------------------------------------------ Compras e Estoque

def exportar_compras(cursor) -> dict:
    fornecedores = consultar(cursor, """
        SELECT f.fornecedor_key, f.razao_social, MIN(p.categoria)
        FROM dw.dim_fornecedor f JOIN dw.dim_produto p ON p.fornecedor_key = f.fornecedor_key
        GROUP BY f.fornecedor_key, f.razao_social ORDER BY f.razao_social""")
    produtos = consultar(cursor, """
        SELECT p.produto_key, p.descricao, p.categoria, p.fornecedor_key, a.classe_abc, a.ranking
        FROM dw.dim_produto p JOIN dw.vw_curva_abc_produto a ON a.produto_key = p.produto_key
        ORDER BY a.ranking, p.cod_produto""")
    categorias = sorted({c for _, _, c in fornecedores})
    indice_forn = {k: i for i, (k, *_) in enumerate(fornecedores)}
    indice_prod = {k: i for i, (k, *_) in enumerate(produtos)}
    # Pontualidade por pedido (todos os itens chegam juntos); cada fornecedor vende uma categoria só
    compras = consultar(cursor, """
        WITH pedidos AS (
            SELECT pedido_numero, fornecedor_key, MIN(data_pedido_key) AS data_key, SUM(valor_total) AS valor,
                   MIN(CASE WHEN entrega_real_key IS NULL THEN 0 ELSE 1 END) AS entregue,
                   MAX(CAST(entregue_no_prazo AS INT)) AS no_prazo, MAX(dias_atraso_entrega) AS atraso
            FROM dw.fato_compra GROUP BY pedido_numero, fornecedor_key)
        SELECT data_key / 100 * 100 + 1, fornecedor_key, SUM(valor), COUNT(*), SUM(entregue),
               SUM(CASE WHEN entregue = 1 THEN no_prazo ELSE 0 END),
               SUM(CASE WHEN entregue = 1 AND atraso > 0 THEN 1 ELSE 0 END),
               SUM(CASE WHEN entregue = 1 AND atraso > 0 THEN atraso ELSE 0 END)
        FROM pedidos GROUP BY data_key / 100 * 100 + 1, fornecedor_key""")
    vendas = consultar(cursor, """
        SELECT data_key / 100 * 100 + 1, produto_key,
               SUM(CASE WHEN tipo_operacao = 'VENDA' THEN qtd_pedida ELSE 0 END),
               SUM(CASE WHEN tipo_operacao = 'VENDA' THEN qtd_faturada ELSE 0 END),
               SUM(CASE WHEN tipo_operacao = 'VENDA'
                        THEN (qtd_pedida - qtd_faturada) * preco_unitario * (1 - desconto_pct / 100) ELSE 0 END),
               SUM(receita_liquida)
        FROM dw.fato_venda GROUP BY data_key / 100 * 100 + 1, produto_key""")
    # Estoque é saldo acumulado dos movimentos (a custo); CMV = saídas por venda menos devoluções
    estoque = consultar(cursor, """
        SELECT data_key / 100 * 100 + 1, produto_key, SUM(valor),
               -SUM(CASE WHEN tipo_movimento IN (N'Saída por venda', N'Devolução de cliente') THEN valor ELSE 0 END)
        FROM dw.fato_estoque_movimento GROUP BY data_key / 100 * 100 + 1, produto_key""")

    meses = sorted({mes(k) for k, *_ in compras} | {mes(k) for k, *_ in vendas} | {mes(k) for k, *_ in estoque})
    indice_mes = {m: i for i, m in enumerate(meses)}
    por_produto = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0.0])
    for k, p, ped, fat, perdida, receita in vendas:
        por_produto[indice_mes[mes(k)], indice_prod[p]][:4] = [int(ped), int(fat), reais(perdida), reais(receita)]
    for k, p, mov, cmv in estoque:
        por_produto[indice_mes[mes(k)], indice_prod[p]][4:] = [reais(mov), reais(cmv)]
    return {
        "gerado_em": date.today().isoformat(),
        "data_corte": "2025-12-31",
        "meses": meses,
        "categorias": categorias,
        "fornecedores": [{"nome": nome, "categoria": categorias.index(c)} for _, nome, c in fornecedores],
        "produtos": [{"nome": nome, "categoria": categorias.index(c), "fornecedor": indice_forn[f], "classe": classe, "ranking": int(r)}
                     for _, nome, c, f, classe, r in produtos],
        # [mês do pedido, fornecedor, valor, pedidos, entregues, no prazo, atrasados, soma dos dias de atraso]
        "compras": [[indice_mes[mes(k)], indice_forn[f], reais(v), *map(int, x)] for k, f, v, *x in compras],
        # [mês, produto, qtd pedida, qtd faturada, venda perdida, receita líquida, movimento de estoque, CMV]
        "produto_mes": [[m, p, *x] for (m, p), x in sorted(por_produto.items())],
    }


def indicadores_compras(dados: dict) -> dict:
    """Recalcula, só com o JSON, os indicadores de dw.vw_conferencia_compras (empresa toda)."""
    meses = dados["meses"]
    ano = lambda i: int(meses[i][:4])
    soma = defaultdict(float)
    for m, _, v, ped, ent, prazo, atras, dias in dados["compras"]:
        for nome, x in (("valor", v), ("pedidos", ped), ("entregues", ent), ("prazo", prazo), ("atrasados", atras), ("dias", dias)):
            soma[ano(m), nome] += x
    movimento = [0.0] * len(meses)
    for m, _, ped, fat, perdida, _, mov, cmv in dados["produto_mes"]:
        soma[ano(m), "pedidas"] += ped; soma[ano(m), "faturadas"] += fat; soma[ano(m), "perdida"] += perdida
        soma[ano(m), "cmv"] += cmv
        movimento[m] += mov
    saldo, saldos = 0.0, defaultdict(list)
    for m, mov in enumerate(movimento):
        saldo += mov
        saldos[ano(m)].append(saldo)

    resultado = {}
    for a in sorted(saldos):
        s = lambda nome: soma[a, nome]
        medio = sum(saldos[a]) / len(saldos[a])
        resultado.update({
            (a, "Valor Comprado"): s("valor"),
            (a, "Pedidos de Compra"): s("pedidos"),
            (a, "Entregas no Prazo %"): s("prazo") / s("entregues"),
            (a, "Atraso Médio quando Atrasa (dias)"): s("dias") / s("atrasados"),
            (a, "Nível de Serviço %"): s("faturadas") / s("pedidas"),
            (a, "Unidades Não Atendidas"): s("pedidas") - s("faturadas"),
            (a, "Venda Perdida por Ruptura"): s("perdida"),
            (a, "Estoque (R$)"): saldos[a][-1],
            (a, "Estoque Médio (R$)"): medio,
            (a, "CMV das Vendas"): s("cmv"),
            (a, "Giro de Estoque"): s("cmv") / medio,
        })
    return resultado


# ------------------------------------------------------------ Comercial

def exportar_comercial(cursor) -> dict:
    filiais = consultar(cursor, "SELECT filial_key, cidade FROM dw.dim_filial ORDER BY filial_key")
    clientes = consultar(cursor, """
        SELECT c.cliente_key, c.razao_social, c.tipo_cliente, c.cidade, c.filial_key, MAX(cal.data)
        FROM dw.dim_cliente c
        LEFT JOIN dw.fato_venda v      ON v.cliente_key = c.cliente_key AND v.tipo_operacao = 'VENDA'
        LEFT JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
        GROUP BY c.cliente_key, c.razao_social, c.tipo_cliente, c.cidade, c.filial_key
        ORDER BY c.cliente_key""")
    vendedores = consultar(cursor, """
        SELECT DISTINCT f.funcionario_key, f.nome, f.cargo
        FROM dw.fato_venda v JOIN dw.dim_funcionario f ON f.funcionario_key = v.vendedor_key
        ORDER BY f.nome""")
    # Mês × cliente × vendedor: dá para filtrar por filial, tipo de cliente e vendedor e ainda contar clientes distintos.
    # O cliente compra sempre na mesma filial, e a numeração das notas é por filial.
    # O valor de tabela não vai no JSON: é faturamento + desconto
    vendas = consultar(cursor, """
        SELECT data_key / 100 * 100 + 1, cliente_key, vendedor_key,
               SUM(valor_desconto), SUM(receita_liquida), SUM(custo_total), COUNT(DISTINCT nf_numero)
        FROM dw.fato_venda WHERE tipo_operacao = 'VENDA'
        GROUP BY data_key / 100 * 100 + 1, cliente_key, vendedor_key""")
    devolucoes = consultar(cursor, """
        SELECT data_key / 100 * 100 + 1, cliente_key, vendedor_key, -SUM(receita_liquida), -SUM(custo_total)
        FROM dw.fato_venda WHERE tipo_operacao = 'DEVOLUCAO'
        GROUP BY data_key / 100 * 100 + 1, cliente_key, vendedor_key""")
    mix = consultar(cursor, """
        SELECT v.data_key / 100 * 100 + 1, v.filial_key, c.tipo_cliente, p.categoria, SUM(v.receita_liquida)
        FROM dw.fato_venda v
        JOIN dw.dim_cliente c ON c.cliente_key = v.cliente_key
        JOIN dw.dim_produto p ON p.produto_key = v.produto_key
        WHERE v.tipo_operacao = 'VENDA'
        GROUP BY v.data_key / 100 * 100 + 1, v.filial_key, c.tipo_cliente, p.categoria""")

    meses = sorted({mes(k) for k, *_ in vendas})
    indice_mes = {m: i for i, m in enumerate(meses)}
    indice_cliente = {k: i for i, (k, *_) in enumerate(clientes)}
    indice_vendedor = {k: i for i, (k, *_) in enumerate(vendedores)}
    tipos = sorted({t for _, _, t, *_ in clientes})
    categorias = sorted({c for _, _, _, c, *_ in mix})
    return {
        "gerado_em": date.today().isoformat(),
        "data_corte": "2025-12-31",
        "meses": meses,
        "filiais": [{"id": f, "nome": nome} for f, nome in filiais],
        "tipos_cliente": tipos,
        "categorias": categorias,
        "clientes": [{"nome": nome, "tipo": tipos.index(t), "cidade": cidade, "filial": f,
                      "ultima_compra": ultima.isoformat() if ultima else None}
                     for _, nome, t, cidade, f, ultima in clientes],
        "vendedores": [{"nome": nome, "cargo": cargo} for _, nome, cargo in vendedores],
        # [mês, cliente, vendedor, desconto, faturamento (já com desconto), custo, notas]
        "vendas": [[indice_mes[mes(k)], indice_cliente[c], indice_vendedor[v], reais(d), reais(fat), reais(cu), int(n)]
                   for k, c, v, d, fat, cu, n in vendas],
        # [mês, cliente, vendedor, valor devolvido, custo devolvido]
        "devolucoes": [[indice_mes[mes(k)], indice_cliente[c], indice_vendedor[v], reais(dv), reais(dc)] for k, c, v, dv, dc in devolucoes],
        # [mês, filial, tipo de cliente, categoria, faturamento]
        "mix": [[indice_mes[mes(k)], f, tipos.index(t), categorias.index(c), reais(fat)] for k, f, t, c, fat in mix],
    }


def indicadores_comercial(dados: dict) -> dict:
    """Recalcula, só com o JSON, os indicadores de dw.vw_conferencia_comercial (empresa toda)."""
    ano = lambda i: int(dados["meses"][i][:4])
    soma = defaultdict(float)
    por_cliente = defaultdict(lambda: defaultdict(float))       # ano -> cliente -> faturamento
    for m, c, _, desconto, fat, custo, notas in dados["vendas"]:
        a = ano(m)
        for nome, x in (("bruto", fat + desconto), ("desconto", desconto), ("fat", fat), ("custo", custo), ("notas", notas)):
            soma[a, nome] += x
        por_cliente[a][c] += fat
    for m, _, _, devol, custo_devol in dados["devolucoes"]:
        soma[ano(m), "devol"] += devol
        soma[ano(m), "custo"] -= custo_devol

    resultado = {}
    for a in sorted(por_cliente):
        s = lambda nome: soma[a, nome]
        liquida = s("fat") - s("devol")
        ranking = sorted(por_cliente[a].values(), reverse=True)
        topo = -(-len(ranking) // 5)                              # NTILE(5): o primeiro quinto leva a sobra
        resultado.update({
            (a, "Faturamento"): s("fat"),
            (a, "Descontos Concedidos"): s("desconto"),
            (a, "Desconto Médio %"): s("desconto") / s("bruto"),
            (a, "Devoluções"): s("devol"),
            (a, "Venda Líquida"): liquida,
            (a, "Custo das Vendas"): s("custo"),
            (a, "Margem Comercial %"): (liquida - s("custo")) / liquida,
            (a, "Notas Fiscais"): s("notas"),
            (a, "Ticket Médio"): s("fat") / s("notas"),
            (a, "Clientes que Compraram"): len(ranking),
            (a, "Faturamento dos 20% Maiores %"): sum(ranking[:topo]) / sum(ranking),
        })
        if a - 1 in por_cliente:
            resultado[a, "Clientes Novos"] = len(por_cliente[a].keys() - por_cliente[a - 1].keys())
            resultado[a, "Clientes Perdidos"] = len(por_cliente[a - 1].keys() - por_cliente[a].keys())
    corte = date.fromisoformat(dados["data_corte"])
    resultado[None, "Clientes sem Compra há Mais de 90 Dias"] = sum(
        1 for c in dados["clientes"] if c["ultima_compra"] and (corte - date.fromisoformat(c["ultima_compra"])).days > 90)
    return resultado


# ------------------------------------------------------------ Excel + automação

PASTA_PONTO = RAIZ / "data" / "bruto" / "rh" / "ponto"
EXTRATO = RAIZ / "data" / "bruto" / "financeiro" / "extrato_bancario_2025_12.csv"
STATUS = ["Conciliado (documento)", "Conciliado (data e valor)", "Valor divergente", "Só no extrato", "Só no sistema"]


def ler_tabela(arquivo: Path, aba: str) -> list[dict]:
    """Lê a tabela que o Power Query gravou na planilha (o resultado que o usuário vê no Excel)."""
    planilha = openpyxl.load_workbook(arquivo, data_only=True)[aba]
    _, ref = next(iter(planilha.tables.items()))
    linhas = list(planilha[ref])
    colunas = [c.value for c in linhas[0]]
    return [dict(zip(colunas, (c.value for c in linha))) for linha in linhas[1:]]


def exportar_excel(cursor) -> dict:
    ponto = ler_tabela(RAIZ / "excel" / "Consolidacao_Ponto.xlsx", "Ponto Consolidado")
    conciliacao = ler_tabela(RAIZ / "excel" / "Conciliacao_Bancaria.xlsx", "Conciliação")

    # Layout de cada arquivo de ponto pelo cabeçalho: em mar/2025 a planilha mudou (horas extras em "hh:mm")
    arquivos = []
    for csv in sorted(PASTA_PONTO.glob("ponto_*.csv")):
        cabecalho = csv.read_text(encoding="utf-8-sig").split("\n", 1)[0]
        arquivos.append({"nome": csv.name, "layout": "novo" if "hh:mm" in cabecalho else "antigo"})
    meses = sorted({linha["Competência"].strftime("%Y-%m") for linha in ponto})
    setores = sorted({linha["Setor"] for linha in ponto})
    resumo = defaultdict(lambda: [0, 0, 0, 0, 0.0])          # pessoas, dias previstos, faltas, atestados, horas extras
    for linha in ponto:
        chave = (meses.index(linha["Competência"].strftime("%Y-%m")), setores.index(linha["Setor"]))
        for i, campo in enumerate(["Dias Previstos", "Faltas", "Dias de Atestado", "Horas Extras"], start=1):
            resumo[chave][i] += linha[campo]
        resumo[chave][0] += 1

    def status(linha):
        return f"Conciliado ({linha['Regra'].lower()})" if linha["Status"] == "Conciliado" else linha["Status"]
    dia = lambda d: d.day if d else None
    valor = lambda v: None if v is None else reais(v)
    return {
        "gerado_em": date.today().isoformat(),
        "meses": meses,
        "setores": setores,
        # [{arquivo, layout}] na ordem dos meses
        "arquivos": arquivos,
        # [mês, setor, pessoas, dias previstos, faltas, dias de atestado, horas extras]
        "ponto": [[m, s, *v[:4], round(v[4], 2)] for (m, s), v in sorted(resumo.items())],
        "conciliacao": {
            "periodo": "2025-12",
            "status": STATUS,
            # [status, dia no extrato, dia no sistema, documento, histórico do banco, descrição no sistema, valor no extrato, valor no sistema]
            "linhas": [[STATUS.index(status(l)), dia(l["Data no Extrato"]), dia(l["Data no Sistema"]), l["Documento"] or "",
                        l["Histórico"] or "", l["Descrição"] or "", valor(l["Valor no Extrato"]), valor(l["Valor no Sistema"])]
                       for l in conciliacao],
        },
    }


def verificar_excel(cursor, dados: dict) -> int:
    """Confere o que o Excel gerou com fontes independentes: o SQL Server e o CSV do banco."""
    ano = lambda m: int(dados["meses"][m][:4])
    soma = defaultdict(float)
    for m, _, pessoas, previstos, faltas, atestados, he in dados["ponto"]:
        for nome, x in (("Registros", pessoas), ("Dias previstos", previstos), ("Faltas", faltas), ("Dias de atestado", atestados), ("Horas extras", he)):
            soma[ano(m), nome] += x
    comparacoes = []
    for a, registros, previstos, faltas, atestados, he in consultar(cursor, """
            SELECT cal.ano, COUNT(*), SUM(p.dias_previstos), SUM(p.faltas), SUM(p.atestado_dias), SUM(p.horas_extras)
            FROM dw.fato_ponto p JOIN dw.dim_calendario cal ON cal.data_key = p.competencia_key GROUP BY cal.ano ORDER BY cal.ano"""):
        for nome, esperado in (("Registros", registros), ("Dias previstos", previstos), ("Faltas", faltas),
                               ("Dias de atestado", atestados), ("Horas extras", he)):
            comparacoes.append((a, f"Ponto: {nome}", float(esperado), soma[a, nome]))

    linhas = dados["conciliacao"]["linhas"]
    no_extrato = [l for l in linhas if l[6] is not None]
    no_sistema = [l for l in linhas if l[7] is not None]
    with open(EXTRATO, "rb") as f:
        linhas_csv = sum(1 for linha in f if linha.strip()) - 1                     # menos o cabeçalho
    (titulos, total), = consultar(cursor, """
        SELECT SUM(n), SUM(v) FROM (
            SELECT COUNT(*) AS n, SUM(valor_pago) AS v FROM dw.fato_conta_receber WHERE pagamento_key BETWEEN 20251201 AND 20251231
            UNION ALL
            SELECT COUNT(*), -SUM(valor_pago) FROM dw.fato_conta_pagar WHERE pagamento_key BETWEEN 20251201 AND 20251231) x""")
    comparacoes += [
        (None, "Conciliação: linhas do extrato (CSV do banco)", float(linhas_csv), float(len(no_extrato))),
        (None, "Conciliação: títulos baixados em dez/2025", float(titulos), float(len(no_sistema))),
        (None, "Conciliação: valor líquido dos títulos", float(total), sum(l[7] for l in no_sistema)),
    ]
    falhas = 0
    for a, indicador, esperado, obtido in comparacoes:
        ok = abs(obtido - esperado) <= 0.01
        falhas += not ok
        print(f"  {'OK   ' if ok else 'FALHA'} {a or 'dez/2025':<8} {indicador:<46} esperado {esperado:>16,.2f}   JSON {obtido:>16,.2f}")
    return falhas


# ------------------------------------------------------------ conferência e gravação

def conferir(cursor, view: str, calculado: dict, ignorar=()) -> int:
    falhas = 0
    for ano, indicador, esperado in consultar(cursor, f"SELECT ano, indicador, valor FROM {view} ORDER BY ordem, ano"):
        if indicador in ignorar:
            continue
        obtido = calculado.get((ano, indicador))
        tolerancia = 1e-6 if "%" in indicador or "dias" in indicador else 0.01
        ok = obtido is not None and abs(obtido - float(esperado)) <= tolerancia
        falhas += not ok
        print(f"  {'OK   ' if ok else 'FALHA'} {ano or 'posição':<8} {indicador:<30} "
              f"SQL {float(esperado):>16,.4f}   JSON {obtido if obtido is None else f'{obtido:>16,.4f}'}")
    return falhas


def pela_view(indicadores, view: str, ignorar=()):
    """Checagem dos painéis de Power BI: recalcula os indicadores da view de conferência a partir do JSON."""
    return lambda cursor, dados: conferir(cursor, view, indicadores(dados), ignorar)


# nome do painel: (exportação, checagem, descrição da checagem)
PAINEIS = {
    "financeiro": (exportar_financeiro, pela_view(indicadores_financeiro, "dw.vw_conferencia_financeiro",
                                                   ("Clientes Inadimplentes", "A Pagar em Aberto")), "dw.vw_conferencia_financeiro"),
    "rh": (exportar_rh, pela_view(indicadores_rh, "dw.vw_conferencia_rh"), "dw.vw_conferencia_rh"),
    "compras": (exportar_compras, pela_view(indicadores_compras, "dw.vw_conferencia_compras"), "dw.vw_conferencia_compras"),
    "comercial": (exportar_comercial, pela_view(indicadores_comercial, "dw.vw_conferencia_comercial"), "dw.vw_conferencia_comercial"),
    "excel": (exportar_excel, verificar_excel, "dw.fato_ponto, títulos no SQL e CSV do banco"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--servidor", default=r"localhost\SQLEXPRESS")
    parser.add_argument("--painel", choices=[*PAINEIS, "todos"], default="todos")
    parser.add_argument("--pasta", type=Path, default=PASTA_PADRAO)
    args = parser.parse_args()

    conexao = conectar(args.servidor, BANCO, escolher_driver())
    cursor = conexao.cursor()
    erros = []
    for nome in PAINEIS if args.painel == "todos" else [args.painel]:
        exportar, verificar, descricao = PAINEIS[nome]
        dados = exportar(cursor)
        print(f"{nome}: conferência com {descricao}")
        falhas = verificar(cursor, dados)
        if falhas:
            erros.append(f"{nome}: {falhas} indicador(es) não bateram, o JSON não foi gravado")
            continue
        saida = args.pasta / f"{nome}.json"
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  gravado {saida} ({saida.stat().st_size / 1024:.0f} KB)")
    conexao.close()
    if erros:
        sys.exit("\n".join(erros))


if __name__ == "__main__":
    main()
