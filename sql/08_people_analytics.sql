/*
  08 - Apoio ao painel de People Analytics

  dw.vw_custo_pessoal         custo de pessoal (salários, encargos e benefícios) por mês, setor e filial
  dw.vw_conferencia_rh        indicadores de RH recalculados em SQL para conferir as medidas DAX

  SELECT * FROM dw.vw_conferencia_rh ORDER BY ordem, ano;
*/
USE DistribuidoraSul;
GO

CREATE OR ALTER VIEW dw.vw_custo_pessoal AS
SELECT d.competencia_key, d.cc_key, d.filial_key, c.cod_conta, c.descricao AS conta, d.valor
FROM dw.fato_dre d
JOIN dw.dim_conta c ON c.conta_key = d.conta_key
WHERE c.grupo_dre = N'Despesas com pessoal';
GO

CREATE OR ALTER VIEW dw.vw_conferencia_rh AS
WITH quadro AS (
    SELECT cal.ano, cal.mes,
           SUM(CAST(q.ativo_inicio_mes AS INT))        AS inicio,
           SUM(CAST(q.ativo_fim_mes AS INT))           AS fim,
           SUM(CAST(q.admitido_no_mes AS INT))         AS admissoes,
           SUM(CAST(q.desligado_no_mes AS INT))        AS desligamentos,
           SUM(CAST(q.desligamento_voluntario AS INT)) AS voluntarios
    FROM dw.fato_quadro_mensal q
    JOIN dw.dim_calendario cal ON cal.data_key = q.competencia_key
    GROUP BY cal.ano, cal.mes
), anual AS (
    SELECT ano,
           SUM(CASE WHEN mes = 12 THEN fim END)       AS headcount_dez,
           AVG((inicio + fim) / 2.0)                  AS headcount_medio,
           SUM(admissoes)                             AS admissoes,
           SUM(desligamentos)                         AS desligamentos,
           SUM(voluntarios)                           AS voluntarios
    FROM quadro
    GROUP BY ano
), experiencia AS (
    SELECT YEAR(data_desligamento) AS ano, COUNT(*) AS desligados_experiencia
    FROM dw.dim_funcionario
    WHERE tempo_casa_meses < 3 AND data_desligamento IS NOT NULL
    GROUP BY YEAR(data_desligamento)
), ponto AS (
    SELECT cal.ano,
           CAST(SUM(p.faltas + p.atestado_dias) AS DECIMAL(18, 6)) / SUM(p.dias_previstos) AS absenteismo,
           SUM(p.horas_extras)                                                          AS horas_extras
    FROM dw.fato_ponto p
    JOIN dw.dim_calendario cal ON cal.data_key = p.competencia_key
    GROUP BY cal.ano
), custo AS (
    SELECT cal.ano, SUM(c.valor) AS custo
    FROM dw.vw_custo_pessoal c
    JOIN dw.dim_calendario cal ON cal.data_key = c.competencia_key
    GROUP BY cal.ano
)
SELECT a.ano, v.ordem, v.indicador, v.valor
FROM anual a
LEFT JOIN experiencia e ON e.ano = a.ano
JOIN ponto p ON p.ano = a.ano
JOIN custo c ON c.ano = a.ano
CROSS APPLY (VALUES
    (1, N'Headcount', CAST(a.headcount_dez AS DECIMAL(24, 6))),
    (2, N'Headcount Médio', CAST(a.headcount_medio AS DECIMAL(24, 6))),
    (3, N'Admissões', CAST(a.admissoes AS DECIMAL(24, 6))),
    (4, N'Desligamentos', CAST(a.desligamentos AS DECIMAL(24, 6))),
    (5, N'Turnover %', CAST(a.desligamentos / a.headcount_medio AS DECIMAL(24, 6))),
    (6, N'Turnover Voluntário %', CAST(a.voluntarios / a.headcount_medio AS DECIMAL(24, 6))),
    (7, N'Desligamentos na Experiência', CAST(ISNULL(e.desligados_experiencia, 0) AS DECIMAL(24, 6))),
    (8, N'Absenteísmo %', CAST(p.absenteismo AS DECIMAL(24, 6))),
    (9, N'Horas Extras', CAST(p.horas_extras AS DECIMAL(24, 6))),
    (10, N'Custo de Pessoal', CAST(c.custo AS DECIMAL(24, 6)))
) AS v (ordem, indicador, valor);
GO
