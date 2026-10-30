# SQL na prática

Dez perguntas de negócio da Distribuidora Sul respondidas em SQL Server, sobre o modelo estrela do schema `dw`. Cada arquivo tem no cabeçalho a pergunta, as técnicas usadas e a leitura do resultado.

A [página do portfólio](https://lucasgama.vercel.app/sql.html) mostra cada consulta com o resultado. Os resultados são gravados por [`python/exportar_web.py`](../../python/exportar_web.py) (`--painel sql`), que roda os arquivos desta pasta e, antes de gravar, confere com as views de conferência os 10 números que eles têm em comum com os painéis.

| # | Pergunta | Técnicas |
|---|---|---|
| 01 | [Quanto cada categoria faturou em 2024 e em 2025, e quanto cresceu?](01_faturamento_por_categoria.sql) | agregação condicional, `ROLLUP`, `NULLIF` |
| 02 | [Em que setores as pessoas saem antes de completar um ano de casa?](02_saidas_no_primeiro_ano.sql) | contagem condicional, média de 0 e 1 como percentual |
| 03 | [Quais fornecedores atrasam mais de 30% dos pedidos?](03_fornecedores_que_atrasam.sql) | CTE, agregação em dois níveis, `HAVING` |
| 04 | [Quem comprou em 2024 e não comprou nada em 2025?](04_clientes_perdidos.sql) | anti-join com `NOT EXISTS` |
| 05 | [Quais são os três produtos que mais faturaram em cada categoria em 2025?](05_top3_produtos_por_categoria.sql) | `ROW_NUMBER` com `PARTITION BY`, janela sobre agregação |
| 06 | [Como o faturamento de 2025 variou contra o mês anterior e contra o mesmo mês de 2024?](06_crescimento_mensal.sql) | `LAG`, filtro aplicado depois da janela |
| 07 | [Mês a mês, quanto da receita orçada para 2025 já tinha sido realizada?](07_receita_acumulada_vs_orcamento.sql) | `UNION ALL`, soma acumulada com `SUM OVER (ORDER BY)` |
| 08 | [O absenteísmo está subindo ou caindo?](08_absenteismo_media_movel.sql) | média móvel com `ROWS BETWEEN` |
| 09 | [Quanto do faturamento de 2025 vem dos 20% maiores clientes?](09_concentracao_de_clientes.sql) | `NTILE`, percentual do total com `SUM() OVER ()` |
| 10 | [Toda nota de venda virou título a receber, com o mesmo valor?](10_notas_x_titulos.sql) | `FULL JOIN` para conciliar duas fontes |

Para rodar uma consulta, abra o arquivo no SSMS ou no Azure Data Studio conectado ao banco `DistribuidoraSul` (criado por `python/carregar_sql.py`).
