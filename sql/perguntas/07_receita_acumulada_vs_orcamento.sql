/*
  Pergunta: Mês a mês, quanto da receita orçada para 2025 já tinha sido realizada?
  Técnicas: UNION ALL para empilhar realizado e orçado, soma acumulada com SUM OVER (ORDER BY)
  Leitura: A receita ficou abaixo do orçado em todos os meses do acumulado. A diferença chegou a
  −6,2% em fevereiro, quase foi recuperada até maio (−0,6%) e o ano fechou com 98,5% do
  orçamento.
*/
WITH lancamentos AS (
    SELECT d.competencia_key, d.valor AS realizado, 0 AS orcado
    FROM dw.fato_dre d
    JOIN dw.dim_conta c ON c.conta_key = d.conta_key
    WHERE c.cod_conta = '3.01'
    UNION ALL
    SELECT o.competencia_key, 0, o.valor
    FROM dw.fato_orcamento o
    JOIN dw.dim_conta c ON c.conta_key = o.conta_key
    WHERE c.cod_conta = '3.01'
), mensal AS (
    SELECT cal.mes, MIN(cal.mes_ano) AS mes_ano, SUM(l.realizado) AS realizado, SUM(l.orcado) AS orcado
    FROM lancamentos l
    JOIN dw.dim_calendario cal ON cal.data_key = l.competencia_key
    WHERE cal.ano = 2025
    GROUP BY cal.mes
)
SELECT mes_ano, realizado,
       SUM(realizado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) AS realizado_acumulado,
       SUM(orcado)    OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) AS orcado_acumulado,
       SUM(realizado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING)
           / SUM(orcado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) - 1 AS pct_desvio_acumulado,
       SUM(realizado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING)
           / SUM(orcado) OVER () AS pct_do_orcamento_anual
FROM mensal
ORDER BY mes;
