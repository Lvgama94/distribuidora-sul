/*
  07 - Números de conferência do painel Financeiro

  SELECT * FROM dw.vw_conferencia_financeiro ORDER BY ordem, ano;

  Calcula em SQL, por outro caminho, os mesmos indicadores das medidas DAX
  (powerbi/Financeiro.SemanticModel). Os cartões do painel têm que bater com
  esta view; se não baterem, a medida ou o filtro do visual está errado.
*/
USE DistribuidoraSul;
GO
CREATE OR ALTER VIEW dw.vw_conferencia_financeiro AS
WITH dre AS (
    SELECT cal.ano,
           SUM(CASE WHEN c.cod_conta = '3.01' THEN d.valor END)              AS receita_bruta,
           SUM(CASE WHEN c.cod_conta IN ('3.02', '3.03') THEN d.valor END)   AS deducoes,
           SUM(CASE WHEN c.grupo_dre = N'CMV' THEN d.valor END)              AS cmv,
           SUM(CASE WHEN c.ordem_grupo BETWEEN 4 AND 7 THEN d.valor END)     AS despesas_operacionais,
           SUM(d.valor_resultado)                                            AS resultado_liquido
    FROM dw.fato_dre d
    JOIN dw.dim_conta c        ON c.conta_key = d.conta_key
    JOIN dw.dim_calendario cal ON cal.data_key = d.competencia_key
    GROUP BY cal.ano
), orcamento AS (
    SELECT cal.ano,
           SUM(o.valor * c.sinal)                                 AS resultado_orcado,
           SUM(CASE WHEN c.cod_conta = '3.01' THEN o.valor END)   AS receita_orcada
    FROM dw.fato_orcamento o
    JOIN dw.dim_conta c        ON c.conta_key = o.conta_key
    JOIN dw.dim_calendario cal ON cal.data_key = o.competencia_key
    GROUP BY cal.ano
), recebimentos AS (
    SELECT cal.ano,
           SUM(r.valor_pago) AS recebido,
           SUM(r.valor * r.prazo_real_dias) / SUM(r.valor) AS pmr,
           SUM(r.valor * r.prazo_concedido_dias) / SUM(r.valor) AS prazo_concedido
    FROM dw.fato_conta_receber r
    JOIN dw.dim_calendario cal ON cal.data_key = r.pagamento_key
    GROUP BY cal.ano
), pagamentos AS (
    SELECT cal.ano,
           SUM(p.valor_pago) AS pago,
           SUM(CASE WHEN c.cod_conta = '1.05' THEN p.valor * p.prazo_real_dias END)
               / SUM(CASE WHEN c.cod_conta = '1.05' THEN p.valor END) AS pmp
    FROM dw.fato_conta_pagar p
    JOIN dw.dim_conta c        ON c.conta_key = p.conta_key
    JOIN dw.dim_calendario cal ON cal.data_key = p.pagamento_key
    GROUP BY cal.ano
), anual AS (
    SELECT d.ano, v.ordem, v.indicador, v.valor
    FROM dre d
    JOIN orcamento o    ON o.ano = d.ano
    JOIN recebimentos r ON r.ano = d.ano
    JOIN pagamentos p   ON p.ano = d.ano
    CROSS APPLY (VALUES
        (1,  N'Receita Bruta',            CAST(d.receita_bruta AS DECIMAL(24, 6))),
        (2,  N'Receita Líquida',          CAST(d.receita_bruta - d.deducoes AS DECIMAL(24, 6))),
        (3,  N'CMV',                      CAST(d.cmv AS DECIMAL(24, 6))),
        (4,  N'Lucro Bruto',              CAST(d.receita_bruta - d.deducoes - d.cmv AS DECIMAL(24, 6))),
        (5,  N'Margem Bruta %',           CAST((d.receita_bruta - d.deducoes - d.cmv) / (d.receita_bruta - d.deducoes) AS DECIMAL(24, 6))),
        (6,  N'Despesas Operacionais',    CAST(d.despesas_operacionais AS DECIMAL(24, 6))),
        (7,  N'Resultado Líquido',        CAST(d.resultado_liquido AS DECIMAL(24, 6))),
        (8,  N'Margem Líquida %',         CAST(d.resultado_liquido / (d.receita_bruta - d.deducoes) AS DECIMAL(24, 6))),
        (9,  N'Receita Orçada',           CAST(o.receita_orcada AS DECIMAL(24, 6))),
        (10, N'Atingimento da Receita %', CAST(d.receita_bruta / o.receita_orcada AS DECIMAL(24, 6))),
        (11, N'Resultado Orçado',         CAST(o.resultado_orcado AS DECIMAL(24, 6))),
        (12, N'Desvio do Resultado',      CAST(d.resultado_liquido - o.resultado_orcado AS DECIMAL(24, 6))),
        (13, N'Recebido',                 CAST(r.recebido AS DECIMAL(24, 6))),
        (14, N'Pago',                     CAST(p.pago AS DECIMAL(24, 6))),
        (15, N'Geração de Caixa',         CAST(r.recebido - p.pago AS DECIMAL(24, 6))),
        (16, N'PMR (dias)',               CAST(r.pmr AS DECIMAL(24, 6))),
        (17, N'Prazo Médio Concedido (dias)', CAST(r.prazo_concedido AS DECIMAL(24, 6))),
        (18, N'PMP (dias)',               CAST(p.pmp AS DECIMAL(24, 6)))
    ) AS v (ordem, indicador, valor)
), posicao AS (
    -- Fotografia na data de corte: não depende do ano
    SELECT CAST(NULL AS SMALLINT) AS ano, v.ordem, v.indicador, v.valor
    FROM (SELECT SUM(CASE WHEN status <> 'PAGO' THEN valor END)                    AS carteira,
                 SUM(CASE WHEN status = 'VENCIDO' THEN valor END)                  AS vencido,
                 SUM(CASE WHEN faixa_aging = N'Mais de 90 dias' THEN valor END)    AS acima_90,
                 COUNT(DISTINCT CASE WHEN status = 'VENCIDO' THEN cliente_key END) AS clientes
          FROM dw.fato_conta_receber) r
    CROSS JOIN (SELECT SUM(CASE WHEN status <> 'PAGO' THEN valor END) AS a_pagar
                FROM dw.fato_conta_pagar) p
    CROSS APPLY (VALUES
        (20, N'Carteira em Aberto',          CAST(r.carteira AS DECIMAL(24, 6))),
        (21, N'Vencido',                     CAST(r.vencido AS DECIMAL(24, 6))),
        (22, N'Vencido há Mais de 90 Dias',  CAST(r.acima_90 AS DECIMAL(24, 6))),
        (23, N'Inadimplência %',             CAST(r.vencido / r.carteira AS DECIMAL(24, 6))),
        (24, N'Clientes Inadimplentes',      CAST(r.clientes AS DECIMAL(24, 6))),
        (25, N'A Pagar em Aberto',           CAST(p.a_pagar AS DECIMAL(24, 6)))
    ) AS v (ordem, indicador, valor)
)
SELECT ano, ordem, indicador, valor FROM anual
UNION ALL
SELECT ano, ordem, indicador, valor FROM posicao;
GO
