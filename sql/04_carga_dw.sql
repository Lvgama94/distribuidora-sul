/*
  04 - Carga do modelo estrela a partir do staging

  EXEC dw.sp_carregar_dw;                         -- data de corte padrão 31/12/2025
  EXEC dw.sp_carregar_dw @data_corte = '2025-12-31';

  Recarrega tudo dentro de uma transação: se algo falhar, o modelo anterior
  continua intacto. No fim devolve a contagem de linhas de cada tabela.
*/
USE DistribuidoraSul;
GO
CREATE OR ALTER PROCEDURE dw.sp_carregar_dw
    @data_corte DATE = '2025-12-31'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Limpa o modelo: fatos primeiro, depois as dimensões (ordem das chaves estrangeiras)
        TRUNCATE TABLE dw.fato_venda;
        TRUNCATE TABLE dw.fato_conta_receber;
        TRUNCATE TABLE dw.fato_conta_pagar;
        TRUNCATE TABLE dw.fato_compra;
        TRUNCATE TABLE dw.fato_orcamento;
        TRUNCATE TABLE dw.fato_dre;
        TRUNCATE TABLE dw.fato_ponto;
        TRUNCATE TABLE dw.fato_estoque_movimento;
        TRUNCATE TABLE dw.fato_quadro_mensal;
        DELETE FROM dw.dim_funcionario;
        DELETE FROM dw.dim_cliente;
        DELETE FROM dw.dim_produto;
        DELETE FROM dw.dim_fornecedor;
        DELETE FROM dw.dim_conta;
        DELETE FROM dw.dim_centro_custo;
        DELETE FROM dw.dim_filial;
        DELETE FROM dw.dim_calendario;

        -- 2. Calendário de 2023 a 2026 (cobre cadastros recentes e vencimentos após o corte)
        WITH numeros AS (
            SELECT TOP (DATEDIFF(DAY, '2023-01-01', '2026-12-31') + 1)
                   ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
            FROM sys.all_objects a CROSS JOIN sys.all_objects b
        ), dias AS (
            SELECT DATEADD(DAY, n, CAST('2023-01-01' AS DATE)) AS data FROM numeros
        )
        INSERT INTO dw.dim_calendario (data_key, data, ano, trimestre, mes, nome_mes, mes_abrev, ano_mes, mes_ano,
                                       semana_iso, dia_semana, nome_dia_semana, feriado, dia_util, primeiro_dia_mes)
        SELECT YEAR(d.data) * 10000 + MONTH(d.data) * 100 + DAY(d.data),
               d.data,
               YEAR(d.data),
               DATEPART(QUARTER, d.data),
               MONTH(d.data),
               CHOOSE(MONTH(d.data), N'Janeiro', N'Fevereiro', N'Março', N'Abril', N'Maio', N'Junho', N'Julho',
                      N'Agosto', N'Setembro', N'Outubro', N'Novembro', N'Dezembro'),
               m.abrev,
               YEAR(d.data) * 100 + MONTH(d.data),
               m.abrev + N'/' + CAST(YEAR(d.data) AS NVARCHAR(4)),
               DATEPART(ISO_WEEK, d.data),
               s.dia_semana,
               CHOOSE(s.dia_semana, N'Segunda-feira', N'Terça-feira', N'Quarta-feira', N'Quinta-feira',
                      N'Sexta-feira', N'Sábado', N'Domingo'),
               CASE WHEN f.data IS NULL THEN 0 ELSE 1 END,
               CASE WHEN s.dia_semana <= 5 AND f.data IS NULL THEN 1 ELSE 0 END,
               DATEFROMPARTS(YEAR(d.data), MONTH(d.data), 1)
        FROM dias d
        CROSS APPLY (SELECT DATEDIFF(DAY, '19000101', d.data) % 7 + 1 AS dia_semana) s   -- 01/01/1900 foi segunda
        CROSS APPLY (SELECT CHOOSE(MONTH(d.data), N'jan', N'fev', N'mar', N'abr', N'mai', N'jun', N'jul', N'ago',
                                   N'set', N'out', N'nov', N'dez') AS abrev) m
        LEFT JOIN dw.feriado f ON f.data = d.data;

        -- 3. Dimensões cadastrais
        INSERT INTO dw.dim_filial (filial_key, nome, cidade, uf)
        SELECT id_filial, nome, cidade, uf FROM stg.filial;

        INSERT INTO dw.dim_centro_custo (cc_key, cod_centro_custo, nome)
        SELECT ROW_NUMBER() OVER (ORDER BY cod_centro_custo), cod_centro_custo, nome FROM stg.centro_custo;

        INSERT INTO dw.dim_conta (conta_key, cod_conta, descricao, grupo_dre, ordem_grupo, sinal, entra_dre)
        SELECT ROW_NUMBER() OVER (ORDER BY cod_conta), cod_conta, descricao, grupo_dre,
               CASE grupo_dre
                    WHEN N'Receita bruta'            THEN 1
                    WHEN N'Deduções da receita'      THEN 2
                    WHEN N'CMV'                      THEN 3
                    WHEN N'Despesas com pessoal'     THEN 4
                    WHEN N'Despesas administrativas' THEN 5
                    WHEN N'Despesas logísticas'      THEN 6
                    WHEN N'Despesas comerciais'      THEN 7
                    WHEN N'Resultado financeiro'     THEN 8
                    ELSE 99 END,
               CASE WHEN grupo_dre = N'Receita bruta' THEN 1 ELSE -1 END,
               CASE WHEN cod_conta LIKE '1.%' THEN 0 ELSE 1 END
        FROM stg.conta;

        INSERT INTO dw.dim_fornecedor (fornecedor_key, cod_fornecedor, razao_social, cnpj, tipo, cidade,
                                       prazo_pagamento_dias, lead_time_dias)
        SELECT ROW_NUMBER() OVER (ORDER BY cod_fornecedor), cod_fornecedor, razao_social, cnpj, tipo, cidade,
               prazo_pagamento_dias, lead_time_dias
        FROM stg.fornecedor;

        INSERT INTO dw.dim_produto (produto_key, cod_produto, descricao, categoria, unidade, fornecedor_key,
                                    fornecedor, preco_tabela_jan2024)
        SELECT ROW_NUMBER() OVER (ORDER BY p.cod_produto), p.cod_produto, p.descricao, p.categoria, p.unidade,
               f.fornecedor_key, f.razao_social, p.preco_tabela_jan2024
        FROM stg.produto p
        JOIN dw.dim_fornecedor f ON f.cod_fornecedor = p.cod_fornecedor;

        INSERT INTO dw.dim_cliente (cliente_key, cod_cliente, razao_social, cnpj, tipo_cliente, cidade, uf,
                                    filial_key, data_cadastro, ano_cadastro, condicao_pagamento, limite_credito,
                                    situacao)
        SELECT ROW_NUMBER() OVER (ORDER BY cod_cliente), cod_cliente, razao_social, cnpj, tipo_cliente, cidade, uf,
               id_filial, data_cadastro, YEAR(data_cadastro), condicao_pagamento, limite_credito, situacao
        FROM stg.cliente;

        INSERT INTO dw.dim_funcionario (funcionario_key, matricula, nome, sexo, data_nascimento, faixa_etaria, cargo,
                                        cc_key, filial_key, data_admissao, data_desligamento, motivo_desligamento,
                                        tipo_desligamento, tempo_casa_meses, faixa_tempo_casa, salario_atual, ativo)
        SELECT ROW_NUMBER() OVER (ORDER BY CAST(f.matricula AS INT)),
               f.matricula, f.nome, f.sexo, f.data_nascimento,
               CASE WHEN f.data_nascimento IS NULL THEN N'Não informada'
                    WHEN i.idade < 25 THEN N'Até 24 anos'
                    WHEN i.idade < 35 THEN N'25 a 34 anos'
                    WHEN i.idade < 45 THEN N'35 a 44 anos'
                    WHEN i.idade < 55 THEN N'45 a 54 anos'
                    ELSE N'55 anos ou mais' END,
               f.cargo, cc.cc_key, f.id_filial, f.data_admissao, f.data_desligamento,
               NULLIF(f.motivo_desligamento, N''),
               CASE WHEN f.data_desligamento IS NULL THEN NULL
                    WHEN f.motivo_desligamento = N'Pedido de demissão' THEN N'Voluntário'
                    ELSE N'Involuntário' END,
               t.meses,
               CASE WHEN t.meses < 3  THEN N'Até 3 meses'
                    WHEN t.meses < 12 THEN N'3 a 12 meses'
                    WHEN t.meses < 24 THEN N'1 a 2 anos'
                    WHEN t.meses < 60 THEN N'2 a 5 anos'
                    ELSE N'Mais de 5 anos' END,
               f.salario_atual,
               CASE WHEN f.data_desligamento IS NULL THEN 1 ELSE 0 END
        FROM stg.funcionario f
        JOIN dw.dim_centro_custo cc ON cc.cod_centro_custo = f.cod_centro_custo
        CROSS APPLY (SELECT ISNULL(f.data_desligamento, @data_corte) AS ref) r
        CROSS APPLY (SELECT DATEDIFF(YEAR, f.data_nascimento, r.ref)
                            - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, f.data_nascimento, r.ref), f.data_nascimento) > r.ref
                                   THEN 1 ELSE 0 END AS idade) i
        CROSS APPLY (SELECT DATEDIFF(MONTH, f.data_admissao, r.ref)
                            - CASE WHEN DAY(r.ref) < DAY(f.data_admissao) THEN 1 ELSE 0 END AS meses) t;

        -- 4. Vendas (só notas faturadas; devoluções entram com quantidade negativa)
        INSERT INTO dw.fato_venda (data_key, filial_key, cliente_key, produto_key, vendedor_key, nf_numero,
                                   tipo_operacao, qtd_pedida, qtd_faturada, preco_unitario, desconto_pct,
                                   valor_bruto, valor_desconto, receita_liquida, custo_total)
        SELECT cal.data_key, v.serie, cli.cliente_key, p.produto_key, fun.funcionario_key, v.nf_numero,
               v.tipo_operacao, v.qtd_pedida, v.qtd_faturada, v.preco_unitario, v.desconto_pct,
               x.bruto, x.bruto - x.liquida, x.liquida,
               ROUND(v.qtd_faturada * v.custo_medio_unitario, 2)
        FROM stg.venda_item v
        JOIN dw.dim_calendario cal  ON cal.data = v.data_emissao
        JOIN dw.dim_cliente cli     ON cli.cod_cliente = v.cod_cliente
        JOIN dw.dim_produto p       ON p.cod_produto = v.cod_produto
        JOIN dw.dim_funcionario fun ON fun.matricula = v.cod_vendedor
        CROSS APPLY (SELECT ROUND(v.qtd_faturada * v.preco_unitario, 2) AS bruto,
                            ROUND(v.qtd_faturada * v.preco_unitario * (1 - v.desconto_pct / 100), 2) AS liquida) x
        WHERE v.status = 'FATURADO';

        -- 5. Contas a receber, com status e aging recalculados na data de corte
        INSERT INTO dw.fato_conta_receber (titulo, cliente_key, filial_key, emissao_key, vencimento_key,
                                           pagamento_key, nf_numero, parcela, valor, valor_pago, juros_multa,
                                           status, dias_atraso, faixa_aging)
        SELECT r.titulo, cli.cliente_key, r.serie, ce.data_key, cv.data_key, cp.data_key, r.nf_numero, r.parcela,
               r.valor, r.valor_pago, ISNULL(r.valor_pago - r.valor, 0), s.status, a.dias_atraso,
               CASE WHEN s.status = 'PAGO'     THEN N'Liquidado'
                    WHEN s.status = 'A VENCER' THEN N'A vencer'
                    WHEN a.dias_atraso <= 30   THEN N'1 a 30 dias'
                    WHEN a.dias_atraso <= 60   THEN N'31 a 60 dias'
                    WHEN a.dias_atraso <= 90   THEN N'61 a 90 dias'
                    ELSE N'Mais de 90 dias' END
        FROM stg.conta_receber r
        JOIN dw.dim_cliente cli    ON cli.cod_cliente = r.cod_cliente
        JOIN dw.dim_calendario ce  ON ce.data = r.data_emissao
        JOIN dw.dim_calendario cv  ON cv.data = r.data_vencimento
        LEFT JOIN dw.dim_calendario cp ON cp.data = r.data_pagamento
        CROSS APPLY (SELECT CASE WHEN r.data_pagamento IS NOT NULL THEN 'PAGO'
                                 WHEN r.data_vencimento >= @data_corte THEN 'A VENCER'
                                 ELSE 'VENCIDO' END AS status) s
        CROSS APPLY (SELECT CASE WHEN s.status = 'PAGO' AND r.data_pagamento > r.data_vencimento
                                      THEN DATEDIFF(DAY, r.data_vencimento, r.data_pagamento)
                                 WHEN s.status = 'VENCIDO' THEN DATEDIFF(DAY, r.data_vencimento, @data_corte)
                                 ELSE 0 END AS dias_atraso) a;

        -- 6. Contas a pagar
        INSERT INTO dw.fato_conta_pagar (id_titulo, fornecedor_key, conta_key, cc_key, filial_key, competencia_key,
                                         emissao_key, vencimento_key, pagamento_key, documento, descricao, valor,
                                         valor_pago, juros_multa, status, dias_atraso)
        SELECT p.id_titulo, f.fornecedor_key, c.conta_key, cc.cc_key, p.id_filial, ccomp.data_key, ce.data_key,
               cv.data_key, cp.data_key, p.documento, p.descricao, p.valor, p.valor_pago,
               ISNULL(p.valor_pago - p.valor, 0), s.status,
               CASE WHEN s.status = 'PAGO' AND p.data_pagamento > p.data_vencimento
                         THEN DATEDIFF(DAY, p.data_vencimento, p.data_pagamento)
                    WHEN s.status = 'VENCIDO' THEN DATEDIFF(DAY, p.data_vencimento, @data_corte)
                    ELSE 0 END
        FROM stg.conta_pagar p
        JOIN dw.dim_fornecedor f      ON f.cod_fornecedor = p.cod_fornecedor
        JOIN dw.dim_conta c           ON c.cod_conta = p.cod_conta
        JOIN dw.dim_centro_custo cc   ON cc.cod_centro_custo = p.cod_centro_custo
        JOIN dw.dim_calendario ccomp  ON ccomp.data = p.competencia
        JOIN dw.dim_calendario ce     ON ce.data = p.data_emissao
        JOIN dw.dim_calendario cv     ON cv.data = p.data_vencimento
        LEFT JOIN dw.dim_calendario cp ON cp.data = p.data_pagamento
        CROSS APPLY (SELECT CASE WHEN p.data_pagamento IS NOT NULL THEN 'PAGO'
                                 WHEN p.data_vencimento >= @data_corte THEN 'A VENCER'
                                 ELSE 'VENCIDO' END AS status) s;

        -- 7. Compras e pontualidade dos fornecedores
        INSERT INTO dw.fato_compra (pedido_numero, data_pedido_key, entrega_prevista_key, entrega_real_key,
                                    fornecedor_key, produto_key, quantidade, custo_unitario, valor_total,
                                    dias_atraso_entrega, entregue_no_prazo, status)
        SELECT c.pedido_numero, cped.data_key, cprev.data_key, creal.data_key, f.fornecedor_key, p.produto_key,
               c.quantidade, c.custo_unitario, ROUND(c.quantidade * c.custo_unitario, 2),
               DATEDIFF(DAY, c.data_entrega_prevista, c.data_entrega_real),
               CASE WHEN c.data_entrega_real IS NULL THEN NULL
                    WHEN c.data_entrega_real <= c.data_entrega_prevista THEN 1 ELSE 0 END,
               c.status
        FROM stg.pedido_compra_item c
        JOIN dw.dim_fornecedor f       ON f.cod_fornecedor = c.cod_fornecedor
        JOIN dw.dim_produto p          ON p.cod_produto = c.cod_produto
        JOIN dw.dim_calendario cped    ON cped.data = c.data_pedido
        JOIN dw.dim_calendario cprev   ON cprev.data = c.data_entrega_prevista
        LEFT JOIN dw.dim_calendario creal ON creal.data = c.data_entrega_real;

        -- 8. Orçamento
        INSERT INTO dw.fato_orcamento (competencia_key, conta_key, cc_key, valor)
        SELECT cal.data_key, c.conta_key, cc.cc_key, o.valor
        FROM stg.orcamento o
        JOIN dw.dim_calendario cal  ON cal.data = o.competencia
        JOIN dw.dim_conta c         ON c.cod_conta = o.cod_conta
        JOIN dw.dim_centro_custo cc ON cc.cod_centro_custo = o.cod_centro_custo;

        -- 9. DRE gerencial realizada (regime de competência)
        --    Receita, devoluções e CMV vêm das vendas; o resto vem do contas a pagar.
        --    Compras de mercadoria (conta 1.05) vão para o estoque e não entram aqui.
        WITH realizado AS (
            SELECT cal.primeiro_dia_mes AS competencia,
                   CASE v.tipo_operacao WHEN 'VENDA' THEN '3.01' ELSE '3.02' END AS cod_conta,
                   'CC02' AS cod_centro_custo, v.filial_key,
                   ABS(SUM(v.receita_liquida)) AS valor
            FROM dw.fato_venda v
            JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
            GROUP BY cal.primeiro_dia_mes, v.tipo_operacao, v.filial_key
            UNION ALL
            SELECT cal.primeiro_dia_mes, '4.01', 'CC02', v.filial_key, SUM(v.custo_total)
            FROM dw.fato_venda v
            JOIN dw.dim_calendario cal ON cal.data_key = v.data_key
            GROUP BY cal.primeiro_dia_mes, v.filial_key
            UNION ALL
            SELECT p.competencia, p.cod_conta, p.cod_centro_custo, p.id_filial, SUM(p.valor)
            FROM stg.conta_pagar p
            WHERE p.cod_conta <> '1.05'
            GROUP BY p.competencia, p.cod_conta, p.cod_centro_custo, p.id_filial
        )
        INSERT INTO dw.fato_dre (competencia_key, conta_key, cc_key, filial_key, valor, valor_resultado)
        SELECT cal.data_key, c.conta_key, cc.cc_key, r.filial_key,
               ROUND(SUM(r.valor), 2), ROUND(SUM(r.valor) * c.sinal, 2)
        FROM realizado r
        JOIN dw.dim_calendario cal  ON cal.data = r.competencia
        JOIN dw.dim_conta c         ON c.cod_conta = r.cod_conta
        JOIN dw.dim_centro_custo cc ON cc.cod_centro_custo = r.cod_centro_custo
        GROUP BY cal.data_key, c.conta_key, cc.cc_key, r.filial_key, c.sinal;

        -- 10. Ponto mensal
        INSERT INTO dw.fato_ponto (competencia_key, funcionario_key, cc_key, dias_previstos, dias_trabalhados, faltas,
                                   atestado_dias, horas_extras)
        SELECT cal.data_key, f.funcionario_key, cc.cc_key,
               p.dias_trabalhados + p.faltas + p.atestado_dias, p.dias_trabalhados, p.faltas, p.atestado_dias,
               p.horas_extras
        FROM stg.ponto_mensal p
        JOIN dw.dim_calendario cal  ON cal.data = p.competencia
        JOIN dw.dim_funcionario f   ON f.matricula = p.matricula
        JOIN dw.dim_centro_custo cc ON cc.cod_centro_custo = p.cod_centro_custo;

        -- 11. Movimentos de estoque (saldo inicial + compras recebidas - vendas + devoluções)
        INSERT INTO dw.fato_estoque_movimento (data_key, produto_key, tipo_movimento, quantidade, valor)
        SELECT cal.data_key, p.produto_key, N'Saldo inicial', e.quantidade, ROUND(e.quantidade * e.custo_medio, 2)
        FROM stg.estoque_inicial e
        JOIN dw.dim_produto p      ON p.cod_produto = e.cod_produto
        JOIN dw.dim_calendario cal ON cal.data = e.data_posicao
        UNION ALL
        SELECT c.entrega_real_key, c.produto_key, N'Entrada por compra', c.quantidade, c.valor_total
        FROM dw.fato_compra c
        WHERE c.entrega_real_key IS NOT NULL
        UNION ALL
        SELECT v.data_key, v.produto_key,
               CASE v.tipo_operacao WHEN 'VENDA' THEN N'Saída por venda' ELSE N'Devolução de cliente' END,
               -v.qtd_faturada, -v.custo_total
        FROM dw.fato_venda v
        WHERE v.qtd_faturada <> 0;

        -- 12. Quadro mensal: uma linha por funcionário em cada mês em que esteve na empresa
        INSERT INTO dw.fato_quadro_mensal (competencia_key, funcionario_key, cc_key, filial_key, ativo_inicio_mes,
                                           ativo_fim_mes, admitido_no_mes, desligado_no_mes, desligamento_voluntario)
        SELECT cal.data_key, f.funcionario_key, f.cc_key, f.filial_key,
               CASE WHEN f.data_admissao < cal.data THEN 1 ELSE 0 END,
               CASE WHEN f.data_desligamento IS NULL OR f.data_desligamento > fm.fim THEN 1 ELSE 0 END,
               CASE WHEN f.data_admissao >= cal.data THEN 1 ELSE 0 END,
               CASE WHEN f.data_desligamento <= fm.fim THEN 1 ELSE 0 END,
               CASE WHEN f.data_desligamento <= fm.fim AND f.tipo_desligamento = N'Voluntário' THEN 1 ELSE 0 END
        FROM dw.dim_calendario cal
        CROSS APPLY (SELECT EOMONTH(cal.data) AS fim) fm
        JOIN dw.dim_funcionario f
          ON f.data_admissao <= fm.fim
         AND (f.data_desligamento IS NULL OR f.data_desligamento >= cal.data)
        WHERE DAY(cal.data) = 1
          AND cal.data BETWEEN '2024-01-01' AND @data_corte;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT 'dim_calendario' AS tabela, COUNT(*) AS linhas FROM dw.dim_calendario
    UNION ALL SELECT 'dim_filial', COUNT(*) FROM dw.dim_filial
    UNION ALL SELECT 'dim_centro_custo', COUNT(*) FROM dw.dim_centro_custo
    UNION ALL SELECT 'dim_conta', COUNT(*) FROM dw.dim_conta
    UNION ALL SELECT 'dim_fornecedor', COUNT(*) FROM dw.dim_fornecedor
    UNION ALL SELECT 'dim_produto', COUNT(*) FROM dw.dim_produto
    UNION ALL SELECT 'dim_cliente', COUNT(*) FROM dw.dim_cliente
    UNION ALL SELECT 'dim_funcionario', COUNT(*) FROM dw.dim_funcionario
    UNION ALL SELECT 'fato_venda', COUNT(*) FROM dw.fato_venda
    UNION ALL SELECT 'fato_conta_receber', COUNT(*) FROM dw.fato_conta_receber
    UNION ALL SELECT 'fato_conta_pagar', COUNT(*) FROM dw.fato_conta_pagar
    UNION ALL SELECT 'fato_compra', COUNT(*) FROM dw.fato_compra
    UNION ALL SELECT 'fato_orcamento', COUNT(*) FROM dw.fato_orcamento
    UNION ALL SELECT 'fato_dre', COUNT(*) FROM dw.fato_dre
    UNION ALL SELECT 'fato_ponto', COUNT(*) FROM dw.fato_ponto
    UNION ALL SELECT 'fato_estoque_movimento', COUNT(*) FROM dw.fato_estoque_movimento
    UNION ALL SELECT 'fato_quadro_mensal', COUNT(*) FROM dw.fato_quadro_mensal;
END;
GO
