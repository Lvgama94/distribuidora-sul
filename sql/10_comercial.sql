/*
  10 - Painel Comercial: números de conferência

  SELECT * FROM dw.vw_conferencia_comercial ORDER BY ordem, ano;

  Calcula em SQL, por outro caminho, os indicadores do painel Comercial. O faturamento é a
  receita bruta da DRE (conta 3.01): vendas já com desconto, antes das devoluções e dos impostos.
  A margem comercial é calculada antes dos impostos, por isso é maior que a margem bruta da DRE.
*/
USE DistribuidoraSul;
GO
CREATE OR ALTER VIEW dw.vw_conferencia_comercial AS
WITH vendas AS (
    SELECT cal.ano,
           SUM(CASE WHEN v.tipo_operacao = 'VENDA' THEN v.receita_liquida END)      AS faturamento,
           SUM(CASE WHEN v.tipo_operacao = 'VENDA' THEN v.valor_bruto END)          AS bruto,
           SUM(CASE WHEN v.tipo_operacao = 'VENDA' THEN v.valor_desconto END)       AS desconto,
           -SUM(CASE WHEN v.tipo_operacao = 'DEVOLUCAO' THEN v.receita_liquida END) AS devolucoes,
           SUM(v.receita_liquida)                                                   AS venda_liquida,
           SUM(v.custo_total)                                                       AS custo,
           -- A numeração das notas é por série, e a série é a filial
           COUNT(DISTINCT CASE WHEN v.tipo_operacao = 'VENDA' THEN CONCAT(v.filial_key, '-', v.nf_numero) END) AS notas,
           COUNT(DISTINCT CASE WHEN v.tipo_operacao = 'VENDA' THEN v.cliente_key END) AS clientes
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    GROUP BY cal.ano
), compradores AS (
    SELECT DISTINCT v.cliente_key, cal.ano
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA'
), ciclo AS (
    -- Novos: compraram no ano e não no anterior. Perdidos: compraram no anterior e não no ano.
    -- Só existe a partir do segundo ano da série.
    SELECT a.ano,
           (SELECT COUNT(*) FROM compradores c
            WHERE c.ano = a.ano AND NOT EXISTS (SELECT 1 FROM compradores p WHERE p.cliente_key = c.cliente_key AND p.ano = a.ano - 1)) AS novos,
           (SELECT COUNT(*) FROM compradores p
            WHERE p.ano = a.ano - 1 AND NOT EXISTS (SELECT 1 FROM compradores c WHERE c.cliente_key = p.cliente_key AND c.ano = a.ano)) AS perdidos
    FROM (SELECT DISTINCT ano FROM compradores WHERE ano > (SELECT MIN(ano) FROM compradores)) a
), concentracao AS (
    -- Fatia do faturamento que vem dos 20% maiores clientes do ano (primeiro quinto do ranking)
    SELECT ano, SUM(CASE WHEN quinto = 1 THEN faturamento END) / SUM(faturamento) AS top20
    FROM (
        SELECT cal.ano, v.cliente_key, SUM(v.receita_liquida) AS faturamento,
               NTILE(5) OVER (PARTITION BY cal.ano ORDER BY SUM(v.receita_liquida) DESC) AS quinto
        FROM dw.fato_venda v
        JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
        WHERE v.tipo_operacao = 'VENDA'
        GROUP BY cal.ano, v.cliente_key
    ) x
    GROUP BY ano
), anual AS (
    SELECT v.ano, x.ordem, x.indicador, x.valor
    FROM vendas v
    JOIN concentracao c ON c.ano = v.ano
    LEFT JOIN ciclo cl  ON cl.ano = v.ano
    CROSS APPLY (VALUES
        (1,  N'Faturamento',                       CAST(v.faturamento AS DECIMAL(24, 6))),
        (2,  N'Descontos Concedidos',              CAST(v.desconto AS DECIMAL(24, 6))),
        (3,  N'Desconto Médio %',                  CAST(v.desconto / v.bruto AS DECIMAL(24, 6))),
        (4,  N'Devoluções',                        CAST(v.devolucoes AS DECIMAL(24, 6))),
        (5,  N'Venda Líquida',                     CAST(v.venda_liquida AS DECIMAL(24, 6))),
        (6,  N'Custo das Vendas',                  CAST(v.custo AS DECIMAL(24, 6))),
        (7,  N'Margem Comercial %',                CAST((v.venda_liquida - v.custo) / v.venda_liquida AS DECIMAL(24, 6))),
        (8,  N'Notas Fiscais',                     CAST(v.notas AS DECIMAL(24, 6))),
        (9,  N'Ticket Médio',                      CAST(v.faturamento / v.notas AS DECIMAL(24, 6))),
        (10, N'Clientes que Compraram',            CAST(v.clientes AS DECIMAL(24, 6))),
        (11, N'Clientes Novos',                    CAST(cl.novos AS DECIMAL(24, 6))),
        (12, N'Clientes Perdidos',                 CAST(cl.perdidos AS DECIMAL(24, 6))),
        (13, N'Faturamento dos 20% Maiores %',     CAST(c.top20 AS DECIMAL(24, 6)))
    ) AS x (ordem, indicador, valor)
    WHERE x.valor IS NOT NULL
), posicao AS (
    -- Fotografia na data de corte: clientes que já compraram e estão há mais de 90 dias sem comprar
    SELECT CAST(NULL AS SMALLINT) AS ano, 20 AS ordem, N'Clientes sem Compra há Mais de 90 Dias' AS indicador,
           CAST(SUM(CASE WHEN DATEDIFF(DAY, ultima, '2025-12-31') > 90 THEN 1 ELSE 0 END) AS DECIMAL(24, 6)) AS valor
    FROM (SELECT v.cliente_key, MAX(cal.data) AS ultima
          FROM dw.fato_venda v
          JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
          WHERE v.tipo_operacao = 'VENDA'
          GROUP BY v.cliente_key) u
)
SELECT ano, ordem, indicador, valor FROM anual
UNION ALL
SELECT ano, ordem, indicador, valor FROM posicao;
GO
