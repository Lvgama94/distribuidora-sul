/*
  02 - Área de staging
  Recebe os CSVs de data/tratado/ sem transformação. Os nomes das colunas são
  iguais aos dos arquivos, então a carga é direta (python/carregar_sql.py).
*/
USE DistribuidoraSul;
GO
DROP TABLE IF EXISTS stg.filial, stg.centro_custo, stg.conta, stg.produto, stg.fornecedor, stg.cliente,
    stg.de_para_cliente, stg.venda_item, stg.pedido_compra_item, stg.estoque_inicial, stg.conta_receber,
    stg.conta_pagar, stg.orcamento, stg.funcionario, stg.ponto_mensal;
GO

CREATE TABLE stg.filial (
    id_filial INT, nome NVARCHAR(60), cidade NVARCHAR(60), uf CHAR(2));

CREATE TABLE stg.centro_custo (
    cod_centro_custo VARCHAR(4), nome NVARCHAR(60));

CREATE TABLE stg.conta (
    cod_conta VARCHAR(5), descricao NVARCHAR(80), grupo_dre NVARCHAR(60));

CREATE TABLE stg.produto (
    cod_produto VARCHAR(5), descricao NVARCHAR(120), categoria NVARCHAR(30), unidade VARCHAR(3),
    cod_fornecedor VARCHAR(4), preco_tabela_jan2024 DECIMAL(12, 2), ativo CHAR(1));

CREATE TABLE stg.fornecedor (
    cod_fornecedor VARCHAR(4), razao_social NVARCHAR(120), cnpj CHAR(14), tipo NVARCHAR(20),
    cidade NVARCHAR(60), prazo_pagamento_dias INT, lead_time_dias INT);

CREATE TABLE stg.cliente (
    cod_cliente VARCHAR(6), razao_social NVARCHAR(150), cnpj CHAR(14), tipo_cliente NVARCHAR(30),
    cidade NVARCHAR(60), uf CHAR(2), id_filial INT, data_cadastro DATE, condicao_pagamento NVARCHAR(20),
    limite_credito DECIMAL(14, 2), situacao VARCHAR(10));

CREATE TABLE stg.de_para_cliente (
    cod_cliente_duplicado VARCHAR(6), cod_mestre VARCHAR(6));

CREATE TABLE stg.venda_item (
    serie INT, nf_numero INT, data_emissao DATE, cod_cliente VARCHAR(6), cod_vendedor VARCHAR(6),
    cod_produto VARCHAR(5), qtd_pedida INT, qtd_faturada INT, preco_unitario DECIMAL(12, 2),
    desconto_pct DECIMAL(5, 2), custo_medio_unitario DECIMAL(14, 4), tipo_operacao VARCHAR(10),
    nf_referencia INT, status VARCHAR(10));

CREATE TABLE stg.pedido_compra_item (
    pedido_numero INT, data_pedido DATE, cod_fornecedor VARCHAR(4), cod_produto VARCHAR(5), quantidade INT,
    custo_unitario DECIMAL(12, 2), data_entrega_prevista DATE, data_entrega_real DATE, status VARCHAR(10));

CREATE TABLE stg.estoque_inicial (
    cod_produto VARCHAR(5), quantidade INT, custo_medio DECIMAL(14, 4), data_posicao DATE);

CREATE TABLE stg.conta_receber (
    titulo VARCHAR(20), serie INT, nf_numero INT, cod_cliente VARCHAR(6), parcela VARCHAR(5),
    data_emissao DATE, data_vencimento DATE, data_pagamento DATE, valor DECIMAL(14, 2),
    valor_pago DECIMAL(14, 2), status VARCHAR(10));

CREATE TABLE stg.conta_pagar (
    id_titulo INT, documento NVARCHAR(40), descricao NVARCHAR(150), cod_conta VARCHAR(5),
    cod_centro_custo VARCHAR(4), id_filial INT, competencia DATE, data_emissao DATE, data_vencimento DATE,
    data_pagamento DATE, valor DECIMAL(14, 2), valor_pago DECIMAL(14, 2), cod_fornecedor VARCHAR(4));

CREATE TABLE stg.orcamento (
    competencia DATE, cod_conta VARCHAR(5), cod_centro_custo VARCHAR(4), valor DECIMAL(14, 2));

CREATE TABLE stg.funcionario (
    matricula VARCHAR(6), nome NVARCHAR(100), sexo CHAR(1), data_nascimento DATE, cargo NVARCHAR(60),
    data_admissao DATE, data_desligamento DATE, motivo_desligamento NVARCHAR(60), salario_atual DECIMAL(12, 2),
    cod_centro_custo VARCHAR(4), id_filial INT);

CREATE TABLE stg.ponto_mensal (
    competencia DATE, matricula VARCHAR(6), cod_centro_custo VARCHAR(4), dias_trabalhados INT, faltas INT,
    atestado_dias INT, horas_extras DECIMAL(6, 2));
GO
