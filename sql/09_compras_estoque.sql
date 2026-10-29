/*
  09 - Apoio ao painel de Compras e Estoque

  dw.vw_conferencia_compras   indicadores de compras, estoque e nível de serviço recalculados em SQL,
                              para conferir as medidas DAX do painel

  SELECT * FROM dw.vw_conferencia_compras ORDER BY ordem, ano;
*/
USE DistribuidoraSul;
GO

CREATE OR ALTER VIEW dw.vw_conferencia_compras AS
WITH compras AS (
    SELECT cal.ano, SUM(c.valor_total) AS valor, COUNT(DISTINCT c.pedido_numero) AS pedidos
    FROM dw.fato_compra c
    JOIN dw.dim_calendario cal ON cal.data_key = c.data_pedido_key
    GROUP BY cal.ano
), pedidos AS (
    -- Pontualidade é medida por pedido (todos os itens de um pedido chegam juntos)
    SELECT pedido_numero, MIN(data_pedido_key) AS data_pedido_key,
           MAX(CAST(entregue_no_prazo AS INT)) AS no_prazo, MAX(dias_atraso_entrega) AS atraso
    FROM dw.fato_compra
    WHERE entrega_real_key IS NOT NULL
    GROUP BY pedido_numero
), pontualidade AS (
    SELECT cal.ano,
           AVG(CAST(p.no_prazo AS DECIMAL(18, 6)))                             AS pct_prazo,
           AVG(CASE WHEN p.atraso > 0 THEN CAST(p.atraso AS DECIMAL(18, 6)) END) AS atraso_medio
    FROM pedidos p
    JOIN dw.dim_calendario cal ON cal.data_key = p.data_pedido_key
    GROUP BY cal.ano
), servico AS (
    SELECT cal.ano,
           SUM(v.qtd_pedida) AS pedidas, SUM(v.qtd_faturada) AS atendidas,
           SUM((v.qtd_pedida - v.qtd_faturada) * v.preco_unitario * (1 - v.desconto_pct / 100)) AS venda_perdida
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA'
    GROUP BY cal.ano
), saldos AS (
    -- Valor do estoque no último dia de cada mês
    SELECT cal.ano, cal.mes,
           (SELECT SUM(m.valor) FROM dw.fato_estoque_movimento m WHERE m.data_key <= cal.data_key) AS saldo
    FROM dw.dim_calendario cal
    WHERE cal.data = EOMONTH(cal.data) AND cal.ano IN (2024, 2025)
), estoque AS (
    SELECT ano, SUM(CASE WHEN mes = 12 THEN saldo END) AS estoque_dez, AVG(saldo) AS estoque_medio
    FROM saldos
    GROUP BY ano
), cmv AS (
    SELECT cal.ano, -SUM(m.valor) AS cmv
    FROM dw.fato_estoque_movimento m
    JOIN dw.dim_calendario cal ON cal.data_key = m.data_key
    WHERE m.tipo_movimento IN (N'Saída por venda', N'Devolução de cliente')
    GROUP BY cal.ano
)
SELECT c.ano, v.ordem, v.indicador, v.valor
FROM compras c
JOIN pontualidade p ON p.ano = c.ano
JOIN servico s      ON s.ano = c.ano
JOIN estoque e      ON e.ano = c.ano
JOIN cmv m          ON m.ano = c.ano
CROSS APPLY (VALUES
    (1,  N'Valor Comprado',                     CAST(c.valor AS DECIMAL(24, 6))),
    (2,  N'Pedidos de Compra',                  CAST(c.pedidos AS DECIMAL(24, 6))),
    (3,  N'Entregas no Prazo %',                CAST(p.pct_prazo AS DECIMAL(24, 6))),
    (4,  N'Atraso Médio quando Atrasa (dias)',  CAST(p.atraso_medio AS DECIMAL(24, 6))),
    (5,  N'Nível de Serviço %',                 CAST(CAST(s.atendidas AS DECIMAL(18, 6)) / s.pedidas AS DECIMAL(24, 6))),
    (6,  N'Unidades Não Atendidas',             CAST(s.pedidas - s.atendidas AS DECIMAL(24, 6))),
    (7,  N'Venda Perdida por Ruptura',          CAST(s.venda_perdida AS DECIMAL(24, 6))),
    (8,  N'Estoque (R$)',                       CAST(e.estoque_dez AS DECIMAL(24, 6))),
    (9,  N'Estoque Médio (R$)',                 CAST(e.estoque_medio AS DECIMAL(24, 6))),
    (10, N'CMV das Vendas',                     CAST(m.cmv AS DECIMAL(24, 6))),
    (11, N'Giro de Estoque',                    CAST(m.cmv / e.estoque_medio AS DECIMAL(24, 6)))
) AS v (ordem, indicador, valor)
WHERE c.ano IN (2024, 2025);
GO
