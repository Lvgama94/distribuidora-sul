/*
  Pergunta: Quem comprou em 2024 e não comprou nada em 2025?
  Técnicas: anti-join com NOT EXISTS, CTE
  Leitura: 49 clientes compraram em 2024 e não voltaram em 2025. Juntos, tinham faturado R$ 4,0
  mi, e só os seis primeiros da lista, todos supermercados, somavam R$ 2,8 mi.
*/
WITH compras_2024 AS (
    SELECT v.cliente_key, SUM(v.receita_liquida) AS faturamento_2024, MAX(cal.data) AS ultima_compra
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA' AND cal.ano = 2024
    GROUP BY v.cliente_key
)
SELECT c.razao_social AS cliente, c.tipo_cliente, c24.faturamento_2024, c24.ultima_compra
FROM compras_2024 c24
JOIN dw.dim_cliente c ON c.cliente_key = c24.cliente_key
WHERE NOT EXISTS (
    SELECT 1
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.cliente_key = c24.cliente_key AND v.tipo_operacao = 'VENDA' AND cal.ano = 2025
)
ORDER BY c24.faturamento_2024 DESC;
