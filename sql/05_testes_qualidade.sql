/*
  05 - Testes de qualidade do modelo

  EXEC dw.sp_testes_qualidade;

  Cada teste conta ocorrências de um problema. Zero ocorrências = OK.
  Rodar depois de cada carga: se algum teste falhar, os números do Power BI
  não devem ser publicados antes de investigar.
*/
USE DistribuidoraSul;
GO
CREATE OR ALTER PROCEDURE dw.sp_testes_qualidade
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @r TABLE (ordem INT IDENTITY, teste NVARCHAR(120), ocorrencias INT);

    -- Completude: nenhuma linha do staging pode se perder nos JOINs da carga
    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Itens faturados do staging que não chegaram à fato_venda',
           (SELECT COUNT(*) FROM stg.venda_item WHERE status = 'FATURADO') - (SELECT COUNT(*) FROM dw.fato_venda);

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Títulos a receber do staging que não chegaram à fato',
           (SELECT COUNT(*) FROM stg.conta_receber) - (SELECT COUNT(*) FROM dw.fato_conta_receber);

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Títulos a pagar do staging que não chegaram à fato',
           (SELECT COUNT(*) FROM stg.conta_pagar) - (SELECT COUNT(*) FROM dw.fato_conta_pagar);

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Registros de ponto sem funcionário ou centro de custo',
           (SELECT COUNT(*) FROM stg.ponto_mensal) - (SELECT COUNT(*) FROM dw.fato_ponto);

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Linhas de orçamento com conta ou centro de custo fora do cadastro',
           (SELECT COUNT(*) FROM stg.orcamento) - (SELECT COUNT(*) FROM dw.fato_orcamento);

    -- Consistência entre áreas: o que foi vendido tem que ter virado título a receber
    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Notas cujo valor difere dos títulos a receber em mais de R$ 0,10', COUNT(*)
    FROM (SELECT filial_key, nf_numero, SUM(receita_liquida) AS vendido
          FROM dw.fato_venda WHERE tipo_operacao = 'VENDA'
          GROUP BY filial_key, nf_numero) n
    FULL JOIN (SELECT filial_key, nf_numero, SUM(valor) AS titulos
               FROM dw.fato_conta_receber
               GROUP BY filial_key, nf_numero) t
           ON t.filial_key = n.filial_key AND t.nf_numero = n.nf_numero
    WHERE ABS(ISNULL(n.vendido, 0) - ISNULL(t.titulos, 0)) > 0.10;

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Receita da DRE diferente da soma das vendas (tolerância R$ 1)',
           CASE WHEN ABS((SELECT SUM(d.valor) FROM dw.fato_dre d JOIN dw.dim_conta c ON c.conta_key = d.conta_key
                          WHERE c.cod_conta = '3.01')
                       - (SELECT SUM(receita_liquida) FROM dw.fato_venda WHERE tipo_operacao = 'VENDA')) > 1
                THEN 1 ELSE 0 END;

    -- Regras de negócio
    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Produto com estoque negativo em algum dia', COUNT(DISTINCT produto_key)
    FROM (SELECT produto_key,
                 SUM(SUM(quantidade)) OVER (PARTITION BY produto_key ORDER BY data_key ROWS UNBOUNDED PRECEDING) AS saldo
          FROM dw.fato_estoque_movimento
          GROUP BY produto_key, data_key) s
    WHERE saldo < 0;

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Título a receber pago antes da emissão', COUNT(*)
    FROM dw.fato_conta_receber WHERE pagamento_key < emissao_key;

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Venda com preço acima de 10x o preço de tabela', COUNT(*)
    FROM dw.fato_venda v JOIN dw.dim_produto p ON p.produto_key = v.produto_key
    WHERE v.preco_unitario > p.preco_tabela_jan2024 * 10;

    INSERT INTO @r (teste, ocorrencias)
    SELECT N'Funcionário desligado antes da admissão', COUNT(*)
    FROM dw.dim_funcionario WHERE data_desligamento < data_admissao;

    SELECT teste, ocorrencias, CASE WHEN ocorrencias = 0 THEN 'OK' ELSE 'FALHA' END AS resultado
    FROM @r ORDER BY ordem;
END;
GO
