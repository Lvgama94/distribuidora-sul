/*
  Pergunta: Quais são os três produtos que mais faturaram em cada categoria em 2025?
  Técnicas: ROW_NUMBER com PARTITION BY, função de janela sobre agregação
  Leitura: Em quatro das seis categorias, o produto líder faz mais de 45% do faturamento da
  categoria. Em Limpeza, o saco de lixo de 100 L sozinho faz 73%: uma ruptura nesse item pesa
  mais que em qualquer outro.
*/
WITH ranking AS (
    SELECT p.categoria, p.descricao AS produto,
           SUM(v.receita_liquida) AS faturamento,
           ROW_NUMBER() OVER (PARTITION BY p.categoria ORDER BY SUM(v.receita_liquida) DESC) AS posicao,
           -- SUM(SUM(...)) OVER: o total da categoria, calculado depois do GROUP BY
           SUM(v.receita_liquida) / SUM(SUM(v.receita_liquida)) OVER (PARTITION BY p.categoria) AS pct_da_categoria
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    JOIN dw.dim_produto p      ON p.produto_key = v.produto_key
    WHERE v.tipo_operacao = 'VENDA' AND cal.ano = 2025
    GROUP BY p.categoria, p.descricao
)
SELECT categoria, posicao, produto, faturamento, pct_da_categoria
FROM ranking
WHERE posicao <= 3
ORDER BY categoria, posicao;
