/*
  Pergunta: O absenteísmo está subindo ou caindo? (com média móvel de 3 meses)
  Técnicas: janela móvel com ROWS BETWEEN, COUNT OVER para descartar janelas incompletas
  Leitura: O absenteísmo médio caiu de 3,1% em 2024 para 2,9% em 2025. A média móvel suaviza
  picos isolados, como abril de 2025 (4,0%), e mostra a tendência entre 2,5% e 3,5% nos dois
  anos.
*/
WITH mensal AS (
    SELECT cal.ano, cal.mes, MIN(cal.mes_ano) AS mes_ano,
           SUM(p.faltas + p.atestado_dias) AS dias_ausentes,
           SUM(p.dias_previstos)           AS dias_previstos
    FROM dw.fato_ponto p
    JOIN dw.dim_calendario cal ON cal.data_key = p.competencia_key
    GROUP BY cal.ano, cal.mes
)
SELECT mes_ano,
       1.0 * dias_ausentes / dias_previstos AS pct_absenteismo,
       -- Soma dos 3 meses dividida pela soma dos 3 meses, e não a média das 3 taxas
       CASE WHEN COUNT(*) OVER (ORDER BY ano, mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) = 3
            THEN 1.0 * SUM(dias_ausentes)  OVER (ORDER BY ano, mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
                     / SUM(dias_previstos) OVER (ORDER BY ano, mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
       END AS pct_media_movel_3_meses
FROM mensal
ORDER BY ano, mes;
