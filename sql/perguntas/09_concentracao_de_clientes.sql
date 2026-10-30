/*
  Pergunta: Quanto do faturamento de 2025 vem dos 20% maiores clientes?
  Técnicas: NTILE, percentual do total com SUM() OVER (), acumulado
  Leitura: Os 75 maiores clientes (20% do total) fazem 73% do faturamento, e os 40% maiores,
  86%. Os 74 menores somam só 2%: perder um cliente grande pesa mais do que perder dezenas de
  pequenos.
*/
WITH por_cliente AS (
    SELECT v.cliente_key, SUM(v.receita_liquida) AS faturamento
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA' AND cal.ano = 2025
    GROUP BY v.cliente_key
), quintos AS (
    -- Divide o ranking de clientes em 5 grupos do mesmo tamanho
    SELECT faturamento, NTILE(5) OVER (ORDER BY faturamento DESC) AS quinto
    FROM por_cliente
)
SELECT CONCAT((quinto - 1) * 20, N'–', quinto * 20, N'% do ranking') AS faixa_de_clientes,
       COUNT(*) AS clientes,
       SUM(faturamento) AS faturamento,
       SUM(faturamento) / SUM(SUM(faturamento)) OVER () AS pct_do_faturamento,
       SUM(SUM(faturamento)) OVER (ORDER BY quinto) / SUM(SUM(faturamento)) OVER () AS pct_acumulado
FROM quintos
GROUP BY quinto
ORDER BY quinto;
