/*
  Pergunta: Quanto cada categoria faturou em 2024 e em 2025, e quanto cresceu?
  Técnicas: agregação condicional (SUM com CASE), ROLLUP, NULLIF
  Leitura: Os dois anos ficam lado a lado sem PIVOT, e o ROLLUP acrescenta a linha de total, que
  é a receita bruta da DRE. Bebidas foi a categoria que mais cresceu (+9,8%) e Higiene, a única
  que caiu (−1,1%).
*/
SELECT CASE WHEN GROUPING(p.categoria) = 1 THEN 'Total' ELSE p.categoria END AS categoria,
       SUM(CASE WHEN cal.ano = 2024 THEN v.receita_liquida END) AS faturamento_2024,
       SUM(CASE WHEN cal.ano = 2025 THEN v.receita_liquida END) AS faturamento_2025,
       SUM(CASE WHEN cal.ano = 2025 THEN v.receita_liquida END)
           / NULLIF(SUM(CASE WHEN cal.ano = 2024 THEN v.receita_liquida END), 0) - 1 AS pct_crescimento
FROM dw.fato_venda v
JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
JOIN dw.dim_produto p      ON p.produto_key = v.produto_key
WHERE v.tipo_operacao = 'VENDA'
GROUP BY ROLLUP (p.categoria)
ORDER BY GROUPING(p.categoria), faturamento_2025 DESC;
