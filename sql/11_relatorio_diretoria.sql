/*
  11 - Relatório para a diretoria: os números das recomendações

  SELECT * FROM dw.vw_relatorio_diretoria ORDER BY ordem;

  Cada número citado no relatório (docs/relatorio_diretoria.md) sai desta view. O impacto de
  faturamento vira lucro bruto descontando os impostos sobre vendas e o custo das mercadorias,
  como na DRE. As premissas de cada estimativa estão nos comentários.
*/
USE DistribuidoraSul;
GO
CREATE OR ALTER VIEW dw.vw_relatorio_diretoria AS
WITH impostos AS (
    -- Impostos sobre vendas de 2025 em % da receita bruta
    SELECT SUM(CASE WHEN c.cod_conta = '3.03' THEN d.valor END)
           / SUM(CASE WHEN c.cod_conta = '3.01' THEN d.valor END) AS taxa
    FROM dw.fato_dre d
    JOIN dw.dim_conta c        ON c.conta_key = d.conta_key
    JOIN dw.dim_calendario cal ON cal.data_key = d.competencia_key
    WHERE cal.ano = 2025
),
-- ------------------------------------------------------------ 1. Clientes que pararam de comprar
clientes AS (
    SELECT v.cliente_key, MAX(cal.data) AS ultima_compra,
           SUM(CASE WHEN cal.ano = 2024 THEN v.receita_liquida END) AS fat_2024,
           SUM(CASE WHEN cal.ano = 2024 THEN v.custo_total END)     AS custo_2024,
           SUM(CASE WHEN cal.ano = 2025 THEN v.receita_liquida END) AS fat_2025
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA'
    GROUP BY v.cliente_key
), parados AS (
    -- Compraram em 2025 e estavam há mais de 90 dias sem comprar em 31/12/2025.
    -- O faturamento de 2024 (ano inteiro de compras) é a base do que está em jogo por ano.
    SELECT COUNT(*) AS clientes, SUM(c.fat_2024) AS fat_2024, SUM(c.custo_2024) AS custo_2024, SUM(c.fat_2025) AS fat_2025,
           SUM(CASE WHEN cli.tipo_cliente = 'Supermercado' THEN 1 ELSE 0 END)          AS supermercados,
           SUM(CASE WHEN cli.tipo_cliente = 'Supermercado' THEN c.fat_2024 END)       AS fat_2024_supermercados
    FROM clientes c
    JOIN dw.dim_cliente cli ON cli.cliente_key = c.cliente_key
    WHERE c.fat_2025 IS NOT NULL AND DATEDIFF(DAY, c.ultima_compra, '2025-12-31') > 90
),
-- ------------------------------------------------------------ 2. Fornecedores que atrasam
pontualidade AS (
    -- Pontualidade de 2025 por fornecedor, medida por pedido (como no painel de Compras)
    SELECT fornecedor_key, AVG(CAST(no_prazo AS DECIMAL(18, 6))) AS pct_no_prazo
    FROM (SELECT c.pedido_numero, c.fornecedor_key, MAX(CAST(c.entregue_no_prazo AS INT)) AS no_prazo
          FROM dw.fato_compra c
          JOIN dw.dim_calendario cal ON cal.data_key = c.data_pedido_key
          WHERE c.entrega_real_key IS NOT NULL AND cal.ano = 2025
          GROUP BY c.pedido_numero, c.fornecedor_key) p
    GROUP BY fornecedor_key
), ruptura AS (
    -- Venda perdida por falta de estoque em 2025, atribuída ao fornecedor principal do produto
    SELECT p.fornecedor_key,
           SUM((v.qtd_pedida - v.qtd_faturada) * v.preco_unitario * (1 - v.desconto_pct / 100)) AS perdida,
           SUM(v.receita_liquida) AS faturado, SUM(v.custo_total) AS custo
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    JOIN dw.dim_produto p      ON p.produto_key = v.produto_key
    WHERE v.tipo_operacao = 'VENDA' AND cal.ano = 2025
    GROUP BY p.fornecedor_key
), grupos AS (
    -- Impontual: menos de 70% dos pedidos de 2025 entregues no prazo
    SELECT CASE WHEN pz.pct_no_prazo < 0.70 THEN 1 ELSE 0 END AS impontual,
           COUNT(*) AS fornecedores, SUM(r.perdida) AS perdida, SUM(r.faturado) AS faturado, SUM(r.custo) AS custo,
           SUM(r.perdida) / (SUM(r.perdida) + SUM(r.faturado)) AS taxa_ruptura
    FROM ruptura r
    JOIN pontualidade pz ON pz.fornecedor_key = r.fornecedor_key
    GROUP BY CASE WHEN pz.pct_no_prazo < 0.70 THEN 1 ELSE 0 END
), fornecedores AS (
    -- Venda perdida a mais: o que deixaria de faltar se os impontuais tivessem a ruptura dos pontuais
    SELECT i.fornecedores, i.perdida, i.taxa_ruptura AS taxa_impontuais, p.taxa_ruptura AS taxa_pontuais,
           i.perdida - p.taxa_ruptura * (i.perdida + i.faturado) AS perdida_a_mais,
           i.custo / i.faturado AS custo_pct
    FROM grupos i
    CROSS JOIN grupos p
    WHERE i.impontual = 1 AND p.impontual = 0
), maior_ruptura AS (
    SELECT TOP 1 r.perdida, pz.pct_no_prazo
    FROM ruptura r
    JOIN pontualidade pz ON pz.fornecedor_key = r.fornecedor_key
    ORDER BY r.perdida DESC
),
-- ------------------------------------------------------------ 3. Saídas no primeiro ano
saidas_ano1 AS (
    SELECT YEAR(data_desligamento) AS ano, cargo, salario_atual
    FROM dw.dim_funcionario
    WHERE data_desligamento BETWEEN '2024-01-01' AND '2025-12-31' AND tempo_casa_meses < 12
), folha AS (
    -- Quanto a empresa gasta por real de salário: (salários + encargos + benefícios) ÷ salários, em 2025
    SELECT SUM(d.valor) / SUM(CASE WHEN c.cod_conta = '5.01' THEN d.valor END) AS multiplicador
    FROM dw.fato_dre d
    JOIN dw.dim_conta c        ON c.conta_key = d.conta_key
    JOIN dw.dim_calendario cal ON cal.data_key = d.competencia_key
    WHERE c.cod_conta IN ('5.01', '5.02', '5.03') AND cal.ano = 2025
), rh AS (
    SELECT COUNT(*) AS saidas_2_anos,
           SUM(CASE WHEN ano = 2025 THEN 1 ELSE 0 END) AS saidas_2025,
           SUM(CASE WHEN cargo IN (N'Ajudante de entrega', N'Vendedor externo') THEN 1 ELSE 0 END) AS ajudantes_vendedores,
           SUM(CASE WHEN ano = 2025 THEN salario_atual END) AS salarios_2025
    FROM saidas_ano1
), vendedores AS (
    SELECT SUM(CASE WHEN YEAR(data_desligamento) = 2024 THEN 1 ELSE 0 END) AS saidas_2024,
           SUM(CASE WHEN YEAR(data_desligamento) = 2025 THEN 1 ELSE 0 END) AS saidas_2025
    FROM dw.dim_funcionario
    WHERE cargo = N'Vendedor externo'
),
-- ------------------------------------------------------------ Também no radar
frota AS (
    SELECT ano, SUM(realizado) - SUM(orcado) AS acima_do_orcado,
           SUM(CASE WHEN cod_conta = '5.09' THEN realizado END) / SUM(CASE WHEN cod_conta = '5.09' THEN orcado END) - 1 AS combustivel_pct,
           SUM(CASE WHEN cod_conta = '5.10' THEN realizado END) / SUM(CASE WHEN cod_conta = '5.10' THEN orcado END) - 1 AS manutencao_pct
    FROM dw.vw_orcado_realizado
    WHERE cod_conta IN ('5.09', '5.10')
    GROUP BY ano
), carteira AS (
    -- Na data de corte. Pequeno varejo: mercados de bairro, padarias e lanchonetes
    SELECT SUM(CASE WHEN r.status = 'VENCIDO' AND r.dias_atraso > 90 THEN r.valor END) AS vencido_90,
           SUM(CASE WHEN r.status = 'VENCIDO' AND cli.tipo_cliente IN (N'Mercado de bairro', N'Padaria', N'Lanchonete') THEN r.valor END)
           / SUM(CASE WHEN r.status <> 'PAGO' AND cli.tipo_cliente IN (N'Mercado de bairro', N'Padaria', N'Lanchonete') THEN r.valor END) AS taxa_pequenos,
           SUM(CASE WHEN r.status = 'VENCIDO' AND cli.tipo_cliente = N'Supermercado' THEN r.valor END)
           / SUM(CASE WHEN r.status <> 'PAGO' AND cli.tipo_cliente = N'Supermercado' THEN r.valor END) AS taxa_supermercados
    FROM dw.fato_conta_receber r
    JOIN dw.dim_cliente cli ON cli.cliente_key = r.cliente_key
), estoque AS (
    SELECT SUM(CASE WHEN ano = 2024 AND indicador = N'Estoque (R$)' THEN valor END)   AS estoque_2024,
           SUM(CASE WHEN ano = 2025 AND indicador = N'Estoque (R$)' THEN valor END)   AS estoque_2025,
           SUM(CASE WHEN ano = 2024 AND indicador = N'Giro de Estoque' THEN valor END) AS giro_2024,
           SUM(CASE WHEN ano = 2025 AND indicador = N'Giro de Estoque' THEN valor END) AS giro_2025
    FROM dw.vw_conferencia_compras
), resultado AS (
    SELECT valor AS resultado_2025
    FROM dw.vw_conferencia_financeiro
    WHERE ano = 2025 AND indicador = N'Resultado Líquido'
), ganho AS (
    -- As três decisões no cenário conservador: 1 em cada 3 clientes de volta, ruptura dos impontuais
    -- igual à dos pontuais e metade das saídas no primeiro ano
    SELECT (pa.fat_2024 * (1 - im.taxa) - pa.custo_2024) / 3
           + fo.perdida_a_mais * (1 - im.taxa - fo.custo_pct)
           + rh.salarios_2025 * fl.multiplicador / 2 AS total
    FROM parados pa
    CROSS JOIN impostos im
    CROSS JOIN fornecedores fo
    CROSS JOIN rh
    CROSS JOIN folha fl
)
-- Cada valor é convertido no VALUES: sem isso, o tipo comum das linhas cortaria os percentuais em 2 casas
SELECT x.ordem, x.secao, x.indicador, x.valor
FROM parados pa
CROSS JOIN impostos im
CROSS JOIN fornecedores fo
CROSS JOIN maior_ruptura mr
CROSS JOIN rh
CROSS JOIN folha fl
CROSS JOIN vendedores ve
CROSS JOIN (SELECT * FROM frota WHERE ano = 2025) f25
CROSS JOIN (SELECT * FROM frota WHERE ano = 2024) f24
CROSS JOIN carteira ca
CROSS JOIN estoque es
CROSS JOIN resultado re
CROSS JOIN ganho ga
CROSS APPLY (VALUES
    (1,  N'Clientes',     N'Clientes que compraram em 2025 e estão parados há mais de 90 dias', CAST(pa.clientes AS DECIMAL(24, 6))),
    (2,  N'Clientes',     N'Faturamento desses clientes em 2024',                     CAST(pa.fat_2024 AS DECIMAL(24, 6))),
    (3,  N'Clientes',     N'Faturamento desses clientes em 2025, até pararem',        CAST(pa.fat_2025 AS DECIMAL(24, 6))),
    (4,  N'Clientes',     N'Supermercados entre eles',                                CAST(pa.supermercados AS DECIMAL(24, 6))),
    (5,  N'Clientes',     N'Faturamento dos supermercados em 2024',                   CAST(pa.fat_2024_supermercados AS DECIMAL(24, 6))),
    (6,  N'Clientes',     N'Lucro bruto desses clientes por ano (base 2024)',         CAST(pa.fat_2024 * (1 - im.taxa) - pa.custo_2024 AS DECIMAL(24, 6))),
    (7,  N'Clientes',     N'Lucro bruto recuperado com 1 em cada 3 clientes',         CAST((pa.fat_2024 * (1 - im.taxa) - pa.custo_2024) / 3 AS DECIMAL(24, 6))),
    (8,  N'Fornecedores', N'Fornecedores com menos de 70% dos pedidos no prazo',      CAST(fo.fornecedores AS DECIMAL(24, 6))),
    (9,  N'Fornecedores', N'Ruptura nos produtos desses fornecedores %',              CAST(fo.taxa_impontuais AS DECIMAL(24, 6))),
    (10, N'Fornecedores', N'Ruptura nos produtos dos demais fornecedores %',          CAST(fo.taxa_pontuais AS DECIMAL(24, 6))),
    (11, N'Fornecedores', N'Venda perdida nos produtos desses fornecedores',          CAST(fo.perdida AS DECIMAL(24, 6))),
    (12, N'Fornecedores', N'Venda perdida a mais que a dos fornecedores pontuais',    CAST(fo.perdida_a_mais AS DECIMAL(24, 6))),
    (13, N'Fornecedores', N'Lucro bruto dessa venda perdida a mais',                  CAST(fo.perdida_a_mais * (1 - im.taxa - fo.custo_pct) AS DECIMAL(24, 6))),
    (14, N'Fornecedores', N'Maior venda perdida de um só fornecedor',                 CAST(mr.perdida AS DECIMAL(24, 6))),
    (15, N'Fornecedores', N'Pedidos no prazo desse fornecedor %',                     CAST(mr.pct_no_prazo AS DECIMAL(24, 6))),
    (16, N'Rotatividade', N'Saídas antes de 1 ano de casa em 2024 e 2025',            CAST(rh.saidas_2_anos AS DECIMAL(24, 6))),
    (17, N'Rotatividade', N'Ajudantes de entrega e vendedores entre elas',            CAST(rh.ajudantes_vendedores AS DECIMAL(24, 6))),
    (18, N'Rotatividade', N'Saídas antes de 1 ano de casa em 2025',                   CAST(rh.saidas_2025 AS DECIMAL(24, 6))),
    (19, N'Rotatividade', N'Saídas de vendedores externos em 2024',                   CAST(ve.saidas_2024 AS DECIMAL(24, 6))),
    (20, N'Rotatividade', N'Saídas de vendedores externos em 2025',                   CAST(ve.saidas_2025 AS DECIMAL(24, 6))),
    (21, N'Rotatividade', N'Custo da folha por real de salário',                      CAST(fl.multiplicador AS DECIMAL(24, 6))),
    -- Premissa: cada substituição custa uma folha mensal completa do cargo (rescisão, seleção e treinamento)
    (22, N'Rotatividade', N'Custo estimado de repor as saídas de 2025',               CAST(rh.salarios_2025 * fl.multiplicador AS DECIMAL(24, 6))),
    (23, N'Rotatividade', N'Economia com metade das saídas',                          CAST(rh.salarios_2025 * fl.multiplicador / 2 AS DECIMAL(24, 6))),
    (24, N'Radar',        N'Frota acima do orçado em 2025',                           CAST(f25.acima_do_orcado AS DECIMAL(24, 6))),
    (25, N'Radar',        N'Frota acima do orçado em 2024',                           CAST(f24.acima_do_orcado AS DECIMAL(24, 6))),
    (26, N'Radar',        N'Combustível acima do orçado em 2025 %',                   CAST(f25.combustivel_pct AS DECIMAL(24, 6))),
    (27, N'Radar',        N'Manutenção acima do orçado em 2025 %',                    CAST(f25.manutencao_pct AS DECIMAL(24, 6))),
    (28, N'Radar',        N'Títulos vencidos há mais de 90 dias',                     CAST(ca.vencido_90 AS DECIMAL(24, 6))),
    (29, N'Radar',        N'Carteira vencida do pequeno varejo %',                    CAST(ca.taxa_pequenos AS DECIMAL(24, 6))),
    (30, N'Radar',        N'Carteira vencida dos supermercados %',                    CAST(ca.taxa_supermercados AS DECIMAL(24, 6))),
    (31, N'Radar',        N'Estoque em dez/2024',                                     CAST(es.estoque_2024 AS DECIMAL(24, 6))),
    (32, N'Radar',        N'Estoque em dez/2025',                                     CAST(es.estoque_2025 AS DECIMAL(24, 6))),
    (33, N'Radar',        N'Giro de estoque 2024',                                    CAST(es.giro_2024 AS DECIMAL(24, 6))),
    (34, N'Radar',        N'Giro de estoque 2025',                                    CAST(es.giro_2025 AS DECIMAL(24, 6))),
    (35, N'Premissas',    N'Impostos sobre vendas em 2025 %',                         CAST(im.taxa AS DECIMAL(24, 6))),
    (36, N'Resumo',       N'Ganho somado das três decisões por ano',                  CAST(ga.total AS DECIMAL(24, 6))),
    (37, N'Resumo',       N'Resultado líquido de 2025',                               CAST(re.resultado_2025 AS DECIMAL(24, 6))),
    (38, N'Resumo',       N'Ganho em % do resultado de 2025',                         CAST(ga.total / re.resultado_2025 AS DECIMAL(24, 6)))
) AS x (ordem, secao, indicador, valor);
GO
