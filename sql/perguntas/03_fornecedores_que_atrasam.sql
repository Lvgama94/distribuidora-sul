/*
  Pergunta: Quais fornecedores atrasam mais de 30% dos pedidos?
  Técnicas: CTE, agregação em dois níveis (item → pedido → fornecedor), HAVING
  Leitura: Nove fornecedores atrasam mais de 30% dos pedidos. A Gaúcha Bebidas Atacado atrasa
  quase metade (48%), com 4,2 dias de atraso médio, e a Gaúcha Alimentos, que é quem mais recebe
  pedidos (156), atrasa 44%.
*/
WITH pedidos AS (
    -- O fato tem uma linha por item; a pontualidade se mede por pedido
    SELECT pedido_numero, fornecedor_key,
           MAX(CAST(entregue_no_prazo AS INT)) AS no_prazo,
           MAX(dias_atraso_entrega)            AS dias_atraso
    FROM dw.fato_compra
    WHERE entrega_real_key IS NOT NULL
    GROUP BY pedido_numero, fornecedor_key
)
SELECT f.razao_social AS fornecedor,
       f.lead_time_dias AS prazo_prometido_dias,
       COUNT(*) AS pedidos,
       SUM(1 - p.no_prazo) AS pedidos_atrasados,
       AVG(1.0 - p.no_prazo) AS pct_atrasados,
       AVG(CASE WHEN p.dias_atraso > 0 THEN 1.0 * p.dias_atraso END) AS atraso_medio_dias
FROM pedidos p
JOIN dw.dim_fornecedor f ON f.fornecedor_key = p.fornecedor_key
GROUP BY f.razao_social, f.lead_time_dias
HAVING AVG(1.0 - p.no_prazo) > 0.30
ORDER BY pct_atrasados DESC;
