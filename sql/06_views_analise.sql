/*
  06 - Views de análise

  Perguntas de negócio respondidas direto em SQL. O Power BI usa as tabelas do
  modelo; estas views servem para conferência e para mostrar a lógica em SQL
  (CTEs, funções de janela e FULL JOIN).
*/
USE DistribuidoraSul;
GO

-- Curva ABC: quais produtos fazem 80% da receita?
CREATE OR ALTER VIEW dw.vw_curva_abc_produto AS
WITH receita AS (
    SELECT p.produto_key, p.cod_produto, p.descricao, p.categoria, SUM(v.receita_liquida) AS receita
    FROM dw.fato_venda v
    JOIN dw.dim_produto p ON p.produto_key = v.produto_key
    GROUP BY p.produto_key, p.cod_produto, p.descricao, p.categoria
), acumulado AS (
    SELECT r.*,
           r.receita / SUM(r.receita) OVER () AS participacao,
           SUM(r.receita) OVER (ORDER BY r.receita DESC, r.cod_produto ROWS UNBOUNDED PRECEDING)
               / SUM(r.receita) OVER () AS participacao_acumulada
    FROM receita r
)
SELECT a.*,
       RANK() OVER (ORDER BY a.receita DESC) AS ranking,
       CASE WHEN a.participacao_acumulada - a.participacao < 0.80 THEN 'A'
            WHEN a.participacao_acumulada - a.participacao < 0.95 THEN 'B'
            ELSE 'C' END AS classe_abc
FROM acumulado a;
GO

-- Orçado x realizado por mês, conta e centro de custo
CREATE OR ALTER VIEW dw.vw_orcado_realizado AS
WITH realizado AS (
    SELECT competencia_key, conta_key, cc_key, SUM(valor) AS realizado
    FROM dw.fato_dre GROUP BY competencia_key, conta_key, cc_key
), orcado AS (
    SELECT competencia_key, conta_key, cc_key, SUM(valor) AS orcado
    FROM dw.fato_orcamento GROUP BY competencia_key, conta_key, cc_key
)
SELECT cal.ano, cal.mes, cal.mes_ano, c.cod_conta, c.descricao AS conta, c.grupo_dre, c.ordem_grupo,
       cc.nome AS centro_custo,
       ISNULL(r.realizado, 0) AS realizado,
       ISNULL(o.orcado, 0) AS orcado,
       ISNULL(r.realizado, 0) - ISNULL(o.orcado, 0) AS desvio,
       (ISNULL(r.realizado, 0) - o.orcado) / NULLIF(o.orcado, 0) AS desvio_pct
FROM realizado r
FULL JOIN orcado o
       ON o.competencia_key = r.competencia_key AND o.conta_key = r.conta_key AND o.cc_key = r.cc_key
JOIN dw.dim_calendario cal  ON cal.data_key = COALESCE(r.competencia_key, o.competencia_key)
JOIN dw.dim_conta c         ON c.conta_key = COALESCE(r.conta_key, o.conta_key)
JOIN dw.dim_centro_custo cc ON cc.cc_key = COALESCE(r.cc_key, o.cc_key);
GO

-- Aging: quem deve, quanto e há quanto tempo (na data de corte)
CREATE OR ALTER VIEW dw.vw_aging_receber AS
SELECT cli.cod_cliente, cli.razao_social, cli.tipo_cliente, f.nome AS filial, r.faixa_aging,
       COUNT(*) AS titulos, SUM(r.valor) AS valor_em_aberto, MAX(r.dias_atraso) AS maior_atraso_dias
FROM dw.fato_conta_receber r
JOIN dw.dim_cliente cli ON cli.cliente_key = r.cliente_key
JOIN dw.dim_filial f    ON f.filial_key = r.filial_key
WHERE r.status <> 'PAGO'
GROUP BY cli.cod_cliente, cli.razao_social, cli.tipo_cliente, f.nome, r.faixa_aging;
GO

-- Rotatividade (turnover) mensal por setor
CREATE OR ALTER VIEW dw.vw_turnover_mensal AS
WITH mensal AS (
    SELECT cal.ano, cal.mes, cal.mes_ano, cc.nome AS setor,
           SUM(CAST(q.ativo_inicio_mes AS INT))        AS headcount_inicio,
           SUM(CAST(q.ativo_fim_mes AS INT))           AS headcount_fim,
           SUM(CAST(q.admitido_no_mes AS INT))         AS admissoes,
           SUM(CAST(q.desligado_no_mes AS INT))        AS desligamentos,
           SUM(CAST(q.desligamento_voluntario AS INT)) AS desligamentos_voluntarios
    FROM dw.fato_quadro_mensal q
    JOIN dw.dim_calendario cal  ON cal.data_key = q.competencia_key
    JOIN dw.dim_centro_custo cc ON cc.cc_key = q.cc_key
    GROUP BY cal.ano, cal.mes, cal.mes_ano, cc.nome
)
SELECT m.*,
       CAST(m.desligamentos AS DECIMAL(9, 4))
           / NULLIF((m.headcount_inicio + m.headcount_fim) / 2.0, 0) AS turnover
FROM mensal m;
GO

-- Pontualidade dos fornecedores (por pedido, não por item)
CREATE OR ALTER VIEW dw.vw_desempenho_fornecedor AS
WITH pedidos AS (
    SELECT pedido_numero, fornecedor_key, MAX(dias_atraso_entrega) AS dias_atraso,
           MAX(CAST(entregue_no_prazo AS INT)) AS no_prazo, SUM(valor_total) AS valor
    FROM dw.fato_compra
    WHERE entrega_real_key IS NOT NULL
    GROUP BY pedido_numero, fornecedor_key
)
SELECT f.cod_fornecedor, f.razao_social, f.lead_time_dias,
       COUNT(*) AS pedidos_entregues,
       SUM(p.valor) AS valor_comprado,
       AVG(CAST(p.no_prazo AS DECIMAL(9, 4))) AS pct_no_prazo,
       AVG(CASE WHEN p.dias_atraso > 0 THEN CAST(p.dias_atraso AS DECIMAL(9, 2)) END) AS atraso_medio_quando_atrasa
FROM pedidos p
JOIN dw.dim_fornecedor f ON f.fornecedor_key = p.fornecedor_key
GROUP BY f.cod_fornecedor, f.razao_social, f.lead_time_dias;
GO

-- Posição de estoque no fim de cada mês, por produto (inclusive meses sem movimento)
CREATE OR ALTER VIEW dw.vw_estoque_fim_mes AS
WITH meses AS (
    SELECT DISTINCT ano_mes FROM dw.dim_calendario WHERE ano IN (2024, 2025)
), movimento AS (
    SELECT cal.ano_mes, m.produto_key, SUM(m.quantidade) AS quantidade, SUM(m.valor) AS valor
    FROM dw.fato_estoque_movimento m
    JOIN dw.dim_calendario cal ON cal.data_key = m.data_key
    GROUP BY cal.ano_mes, m.produto_key
), grade AS (
    SELECT ms.ano_mes, p.produto_key, ISNULL(mv.quantidade, 0) AS quantidade, ISNULL(mv.valor, 0) AS valor
    FROM meses ms
    CROSS JOIN dw.dim_produto p
    LEFT JOIN movimento mv ON mv.ano_mes = ms.ano_mes AND mv.produto_key = p.produto_key
)
SELECT g.ano_mes, p.cod_produto, p.descricao, p.categoria,
       SUM(g.quantidade) OVER (PARTITION BY g.produto_key ORDER BY g.ano_mes ROWS UNBOUNDED PRECEDING) AS saldo_quantidade,
       SUM(g.valor) OVER (PARTITION BY g.produto_key ORDER BY g.ano_mes ROWS UNBOUNDED PRECEDING) AS saldo_valor
FROM grade g
JOIN dw.dim_produto p ON p.produto_key = g.produto_key;
GO
