/*
  Pergunta: Toda nota de venda virou título a receber, com o mesmo valor?
  Técnicas: FULL JOIN para conciliar duas fontes, classificação com CASE
  Leitura: As 22.656 notas de venda dos dois anos viraram 25.588 títulos a receber, sem nota sem
  título e sem valor diferente. Os R$ 8,31 de diferença no total são o arredondamento das
  parcelas, menos de R$ 0,10 por nota.
*/
WITH notas AS (
    -- A numeração das notas é por filial
    SELECT filial_key, nf_numero, MIN(data_key) / 10000 AS ano, SUM(receita_liquida) AS vendido
    FROM dw.fato_venda
    WHERE tipo_operacao = 'VENDA'
    GROUP BY filial_key, nf_numero
), titulos AS (
    -- Uma nota pode ser parcelada em vários títulos
    SELECT filial_key, nf_numero, MIN(emissao_key) / 10000 AS ano, COUNT(*) AS parcelas, SUM(valor) AS a_receber
    FROM dw.fato_conta_receber
    GROUP BY filial_key, nf_numero
), conciliacao AS (
    SELECT COALESCE(n.ano, t.ano) AS ano, n.vendido, t.a_receber, t.parcelas,
           CASE WHEN t.nf_numero IS NULL THEN N'Nota sem título'
                WHEN n.nf_numero IS NULL THEN N'Título sem nota'
                WHEN ABS(n.vendido - t.a_receber) > 0.10 THEN N'Valor diferente'
                ELSE N'Confere' END AS situacao
    FROM notas n
    FULL JOIN titulos t ON t.filial_key = n.filial_key AND t.nf_numero = n.nf_numero
)
SELECT ano, situacao,
       COUNT(*) AS notas,
       SUM(parcelas) AS titulos,
       SUM(vendido) AS vendido,
       SUM(a_receber) AS a_receber,
       ISNULL(SUM(a_receber), 0) - ISNULL(SUM(vendido), 0) AS diferenca
FROM conciliacao
GROUP BY ano, situacao
ORDER BY ano, situacao;
