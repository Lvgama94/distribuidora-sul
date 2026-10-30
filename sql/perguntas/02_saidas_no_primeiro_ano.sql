/*
  Pergunta: Em que setores as pessoas saem antes de completar um ano de casa?
  Técnicas: contagem condicional, média de 0 e 1 como percentual, JOIN com dimensão
  Leitura: Dos 80 desligamentos dos dois anos, 50 (62%) aconteceram antes de um ano de casa. A
  Logística concentra 48 saídas, 65% delas no primeiro ano: é onde um programa de integração
  teria mais efeito.
*/
SELECT cc.nome AS setor,
       COUNT(*) AS desligamentos,
       SUM(CASE WHEN f.tempo_casa_meses < 12 THEN 1 ELSE 0 END) AS antes_de_1_ano,
       -- A média de uma coluna de 0 e 1 é o percentual de casos
       AVG(CASE WHEN f.tempo_casa_meses < 12 THEN 1.0 ELSE 0 END) AS pct_antes_de_1_ano,
       AVG(CASE WHEN f.tipo_desligamento = N'Voluntário' THEN 1.0 ELSE 0 END) AS pct_pediram_demissao,
       AVG(1.0 * f.tempo_casa_meses) AS tempo_medio_de_casa_meses
FROM dw.dim_funcionario f
JOIN dw.dim_centro_custo cc ON cc.cc_key = f.cc_key
WHERE f.data_desligamento BETWEEN '2024-01-01' AND '2025-12-31'
GROUP BY cc.nome
ORDER BY desligamentos DESC;
