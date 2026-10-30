/*
  Pergunta: Como o faturamento de 2025 variou contra o mês anterior e contra o mesmo mês de 2024?
  Técnicas: LAG, CTE, filtro aplicado depois da janela
  Leitura: A comparação com o mesmo mês do ano anterior tira o efeito da sazonalidade: dezembro
  cresceu 32% sobre novembro, mas ficou igual a dezembro de 2024 (−0,1%). Maio cresceu 35% sobre
  uma base fraca, porque as enchentes de maio de 2024 derrubaram as vendas da matriz em Porto
  Alegre.
*/
WITH mensal AS (
    SELECT cal.ano, cal.mes, MIN(cal.mes_ano) AS mes_ano, SUM(v.receita_liquida) AS faturamento
    FROM dw.fato_venda v
    JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
    WHERE v.tipo_operacao = 'VENDA'
    GROUP BY cal.ano, cal.mes
), comparado AS (
    SELECT ano, mes, mes_ano, faturamento,
           LAG(faturamento, 1)  OVER (ORDER BY ano, mes) AS mes_anterior,
           LAG(faturamento, 12) OVER (ORDER BY ano, mes) AS mesmo_mes_ano_anterior
    FROM mensal
)
-- O filtro de 2025 fica aqui, e não na CTE: senão janeiro não teria o dezembro de 2024 para comparar
SELECT mes_ano, faturamento,
       faturamento / mes_anterior - 1           AS pct_vs_mes_anterior,
       faturamento / mesmo_mes_ano_anterior - 1 AS pct_vs_ano_anterior
FROM comparado
WHERE ano = 2025
ORDER BY ano, mes;
