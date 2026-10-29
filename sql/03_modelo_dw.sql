/*
  03 - Modelo estrela (schema dw)

  Dimensões:  calendario, filial, centro_custo, conta, produto, cliente, fornecedor, funcionario
  Fatos:      venda (item de nota)            conta_receber (título)     conta_pagar (título)
              compra (item de pedido)         orcamento (mês x conta x CC)
              dre (mês x conta x CC x filial) ponto (funcionário x mês)
              estoque_movimento (movimento)   quadro_mensal (funcionário x mês)

  As chaves das dimensões são geradas na carga (ROW_NUMBER), por isso não usam IDENTITY.
*/
USE DistribuidoraSul;
GO
DROP TABLE IF EXISTS dw.fato_venda, dw.fato_conta_receber, dw.fato_conta_pagar, dw.fato_compra,
    dw.fato_orcamento, dw.fato_dre, dw.fato_ponto, dw.fato_estoque_movimento, dw.fato_quadro_mensal;
DROP TABLE IF EXISTS dw.dim_funcionario, dw.dim_cliente, dw.dim_produto, dw.dim_fornecedor, dw.dim_conta,
    dw.dim_centro_custo, dw.dim_filial, dw.dim_calendario, dw.feriado;
GO

-- ---------------------------------------------------------------------------
-- Dimensões
-- ---------------------------------------------------------------------------
CREATE TABLE dw.feriado (
    data DATE NOT NULL PRIMARY KEY,
    descricao NVARCHAR(60) NOT NULL
);
INSERT INTO dw.feriado (data, descricao) VALUES
    ('2024-01-01', N'Confraternização Universal'), ('2024-02-12', N'Carnaval'), ('2024-02-13', N'Carnaval'),
    ('2024-03-29', N'Sexta-feira Santa'), ('2024-04-21', N'Tiradentes'), ('2024-05-01', N'Dia do Trabalho'),
    ('2024-05-30', N'Corpus Christi'), ('2024-09-07', N'Independência'), ('2024-09-20', N'Revolução Farroupilha'),
    ('2024-10-12', N'Nossa Senhora Aparecida'), ('2024-11-02', N'Finados'), ('2024-11-15', N'Proclamação da República'),
    ('2024-11-20', N'Consciência Negra'), ('2024-12-25', N'Natal'),
    ('2025-01-01', N'Confraternização Universal'), ('2025-03-03', N'Carnaval'), ('2025-03-04', N'Carnaval'),
    ('2025-04-18', N'Sexta-feira Santa'), ('2025-04-21', N'Tiradentes'), ('2025-05-01', N'Dia do Trabalho'),
    ('2025-06-19', N'Corpus Christi'), ('2025-09-07', N'Independência'), ('2025-09-20', N'Revolução Farroupilha'),
    ('2025-10-12', N'Nossa Senhora Aparecida'), ('2025-11-02', N'Finados'), ('2025-11-15', N'Proclamação da República'),
    ('2025-11-20', N'Consciência Negra'), ('2025-12-25', N'Natal'),
    ('2026-01-01', N'Confraternização Universal'), ('2026-02-16', N'Carnaval'), ('2026-02-17', N'Carnaval'),
    ('2026-04-03', N'Sexta-feira Santa'), ('2026-04-21', N'Tiradentes'), ('2026-05-01', N'Dia do Trabalho'),
    ('2026-06-04', N'Corpus Christi'), ('2026-09-07', N'Independência'), ('2026-09-20', N'Revolução Farroupilha'),
    ('2026-10-12', N'Nossa Senhora Aparecida'), ('2026-11-02', N'Finados'), ('2026-11-15', N'Proclamação da República'),
    ('2026-11-20', N'Consciência Negra'), ('2026-12-25', N'Natal');

CREATE TABLE dw.dim_calendario (
    data_key         INT          NOT NULL PRIMARY KEY,   -- aaaammdd
    data             DATE         NOT NULL UNIQUE,
    ano              SMALLINT     NOT NULL,
    trimestre        TINYINT      NOT NULL,
    mes              TINYINT      NOT NULL,
    nome_mes         NVARCHAR(10) NOT NULL,
    mes_abrev        NVARCHAR(3)  NOT NULL,
    ano_mes          INT          NOT NULL,               -- aaaamm, para ordenar
    mes_ano          NVARCHAR(8)  NOT NULL,               -- jan/2024
    semana_iso       TINYINT      NOT NULL,
    dia_semana       TINYINT      NOT NULL,               -- 1 = segunda-feira
    nome_dia_semana  NVARCHAR(13) NOT NULL,
    feriado          BIT          NOT NULL,
    dia_util         BIT          NOT NULL,               -- segunda a sexta, sem feriado
    primeiro_dia_mes DATE         NOT NULL
);

CREATE TABLE dw.dim_filial (
    filial_key INT          NOT NULL PRIMARY KEY,
    nome       NVARCHAR(60) NOT NULL,
    cidade     NVARCHAR(60) NOT NULL,
    uf         CHAR(2)      NOT NULL
);

CREATE TABLE dw.dim_centro_custo (
    cc_key           INT          NOT NULL PRIMARY KEY,
    cod_centro_custo VARCHAR(4)   NOT NULL UNIQUE,
    nome             NVARCHAR(60) NOT NULL
);

CREATE TABLE dw.dim_conta (
    conta_key   INT          NOT NULL PRIMARY KEY,
    cod_conta   VARCHAR(5)   NOT NULL UNIQUE,
    descricao   NVARCHAR(80) NOT NULL,
    grupo_dre   NVARCHAR(60) NOT NULL,
    ordem_grupo TINYINT      NOT NULL,   -- ordem das linhas na DRE
    sinal       SMALLINT     NOT NULL,   -- +1 soma no resultado, -1 subtrai
    entra_dre   BIT          NOT NULL
);

CREATE TABLE dw.dim_fornecedor (
    fornecedor_key       INT           NOT NULL PRIMARY KEY,
    cod_fornecedor       VARCHAR(4)    NOT NULL UNIQUE,
    razao_social         NVARCHAR(120) NOT NULL,
    cnpj                 CHAR(14)      NOT NULL,
    tipo                 NVARCHAR(20)  NOT NULL,
    cidade               NVARCHAR(60)  NOT NULL,
    prazo_pagamento_dias INT           NULL,
    lead_time_dias       INT           NULL
);

CREATE TABLE dw.dim_produto (
    produto_key          INT           NOT NULL PRIMARY KEY,
    cod_produto          VARCHAR(5)    NOT NULL UNIQUE,
    descricao            NVARCHAR(120) NOT NULL,
    categoria            NVARCHAR(30)  NOT NULL,
    unidade              VARCHAR(3)    NOT NULL,
    fornecedor_key       INT           NOT NULL REFERENCES dw.dim_fornecedor,
    fornecedor           NVARCHAR(120) NOT NULL,
    preco_tabela_jan2024 DECIMAL(12, 2) NOT NULL
);

CREATE TABLE dw.dim_cliente (
    cliente_key        INT            NOT NULL PRIMARY KEY,
    cod_cliente        VARCHAR(6)     NOT NULL UNIQUE,
    razao_social       NVARCHAR(150)  NOT NULL,
    cnpj               CHAR(14)       NOT NULL UNIQUE,
    tipo_cliente       NVARCHAR(30)   NOT NULL,
    cidade             NVARCHAR(60)   NOT NULL,
    uf                 CHAR(2)        NOT NULL,
    filial_key         INT            NOT NULL REFERENCES dw.dim_filial,
    data_cadastro      DATE           NOT NULL,
    ano_cadastro       SMALLINT       NOT NULL,
    condicao_pagamento NVARCHAR(20)   NOT NULL,
    limite_credito     DECIMAL(14, 2) NOT NULL,
    situacao           VARCHAR(10)    NOT NULL
);

CREATE TABLE dw.dim_funcionario (
    funcionario_key     INT            NOT NULL PRIMARY KEY,
    matricula           VARCHAR(6)     NOT NULL UNIQUE,
    nome                NVARCHAR(100)  NOT NULL,
    sexo                CHAR(1)        NOT NULL,
    data_nascimento     DATE           NULL,
    faixa_etaria        NVARCHAR(15)   NOT NULL,   -- idade no desligamento ou na data de corte
    cargo               NVARCHAR(60)   NOT NULL,
    cc_key              INT            NOT NULL REFERENCES dw.dim_centro_custo,
    filial_key          INT            NOT NULL REFERENCES dw.dim_filial,
    data_admissao       DATE           NOT NULL,
    data_desligamento   DATE           NULL,
    motivo_desligamento NVARCHAR(60)   NULL,
    tipo_desligamento   NVARCHAR(15)   NULL,       -- Voluntário / Involuntário
    tempo_casa_meses    INT            NOT NULL,
    faixa_tempo_casa    NVARCHAR(15)   NOT NULL,
    salario_atual       DECIMAL(12, 2) NOT NULL,
    ativo               BIT            NOT NULL
);

-- ---------------------------------------------------------------------------
-- Fatos
-- ---------------------------------------------------------------------------
CREATE TABLE dw.fato_venda (
    venda_key       BIGINT IDENTITY NOT NULL PRIMARY KEY,
    data_key        INT            NOT NULL REFERENCES dw.dim_calendario,
    filial_key      INT            NOT NULL REFERENCES dw.dim_filial,
    cliente_key     INT            NOT NULL REFERENCES dw.dim_cliente,
    produto_key     INT            NOT NULL REFERENCES dw.dim_produto,
    vendedor_key    INT            NOT NULL REFERENCES dw.dim_funcionario,
    nf_numero       INT            NOT NULL,
    tipo_operacao   VARCHAR(10)    NOT NULL,   -- VENDA / DEVOLUCAO (devolução com quantidade negativa)
    qtd_pedida      INT            NOT NULL,
    qtd_faturada    INT            NOT NULL,
    preco_unitario  DECIMAL(12, 2) NOT NULL,
    desconto_pct    DECIMAL(5, 2)  NOT NULL,
    valor_bruto     DECIMAL(14, 2) NOT NULL,
    valor_desconto  DECIMAL(14, 2) NOT NULL,
    receita_liquida DECIMAL(14, 2) NOT NULL,
    custo_total     DECIMAL(14, 2) NOT NULL
);

CREATE TABLE dw.fato_conta_receber (
    titulo         VARCHAR(20)    NOT NULL PRIMARY KEY,
    cliente_key    INT            NOT NULL REFERENCES dw.dim_cliente,
    filial_key     INT            NOT NULL REFERENCES dw.dim_filial,
    emissao_key    INT            NOT NULL REFERENCES dw.dim_calendario,
    vencimento_key INT            NOT NULL REFERENCES dw.dim_calendario,
    pagamento_key  INT            NULL     REFERENCES dw.dim_calendario,
    nf_numero      INT            NOT NULL,
    parcela        VARCHAR(5)     NOT NULL,
    valor          DECIMAL(14, 2) NOT NULL,
    valor_pago     DECIMAL(14, 2) NULL,
    juros_multa    DECIMAL(14, 2) NOT NULL,
    status         VARCHAR(10)    NOT NULL,   -- PAGO / A VENCER / VENCIDO na data de corte
    dias_atraso    INT            NOT NULL,
    faixa_aging    NVARCHAR(16)   NOT NULL
);

CREATE TABLE dw.fato_conta_pagar (
    id_titulo      INT            NOT NULL PRIMARY KEY,
    fornecedor_key INT            NOT NULL REFERENCES dw.dim_fornecedor,
    conta_key      INT            NOT NULL REFERENCES dw.dim_conta,
    cc_key         INT            NOT NULL REFERENCES dw.dim_centro_custo,
    filial_key     INT            NOT NULL REFERENCES dw.dim_filial,
    competencia_key INT           NOT NULL REFERENCES dw.dim_calendario,
    emissao_key    INT            NOT NULL REFERENCES dw.dim_calendario,
    vencimento_key INT            NOT NULL REFERENCES dw.dim_calendario,
    pagamento_key  INT            NULL     REFERENCES dw.dim_calendario,
    documento      NVARCHAR(40)   NOT NULL,
    descricao      NVARCHAR(150)  NOT NULL,
    valor          DECIMAL(14, 2) NOT NULL,
    valor_pago     DECIMAL(14, 2) NULL,
    juros_multa    DECIMAL(14, 2) NOT NULL,
    status         VARCHAR(10)    NOT NULL,
    dias_atraso    INT            NOT NULL
);

CREATE TABLE dw.fato_compra (
    compra_key           BIGINT IDENTITY NOT NULL PRIMARY KEY,
    pedido_numero        INT            NOT NULL,
    data_pedido_key      INT            NOT NULL REFERENCES dw.dim_calendario,
    entrega_prevista_key INT            NOT NULL REFERENCES dw.dim_calendario,
    entrega_real_key     INT            NULL     REFERENCES dw.dim_calendario,
    fornecedor_key       INT            NOT NULL REFERENCES dw.dim_fornecedor,
    produto_key          INT            NOT NULL REFERENCES dw.dim_produto,
    quantidade           INT            NOT NULL,
    custo_unitario       DECIMAL(12, 2) NOT NULL,
    valor_total          DECIMAL(14, 2) NOT NULL,
    dias_atraso_entrega  INT            NULL,
    entregue_no_prazo    BIT            NULL,
    status               VARCHAR(10)    NOT NULL
);

CREATE TABLE dw.fato_orcamento (
    competencia_key INT            NOT NULL REFERENCES dw.dim_calendario,
    conta_key       INT            NOT NULL REFERENCES dw.dim_conta,
    cc_key          INT            NOT NULL REFERENCES dw.dim_centro_custo,
    valor           DECIMAL(14, 2) NOT NULL,
    PRIMARY KEY (competencia_key, conta_key, cc_key)
);

CREATE TABLE dw.fato_dre (
    competencia_key INT            NOT NULL REFERENCES dw.dim_calendario,
    conta_key       INT            NOT NULL REFERENCES dw.dim_conta,
    cc_key          INT            NOT NULL REFERENCES dw.dim_centro_custo,
    filial_key      INT            NOT NULL REFERENCES dw.dim_filial,
    valor           DECIMAL(14, 2) NOT NULL,   -- valor positivo da conta
    valor_resultado DECIMAL(14, 2) NOT NULL,   -- com sinal: receita soma, custos e despesas subtraem
    PRIMARY KEY (competencia_key, conta_key, cc_key, filial_key)
);

CREATE TABLE dw.fato_ponto (
    competencia_key  INT           NOT NULL REFERENCES dw.dim_calendario,
    funcionario_key  INT           NOT NULL REFERENCES dw.dim_funcionario,
    cc_key           INT           NOT NULL REFERENCES dw.dim_centro_custo,
    dias_previstos   INT           NOT NULL,
    dias_trabalhados INT           NOT NULL,
    faltas           INT           NOT NULL,
    atestado_dias    INT           NOT NULL,
    horas_extras     DECIMAL(6, 2) NOT NULL,
    PRIMARY KEY (competencia_key, funcionario_key)
);

CREATE TABLE dw.fato_estoque_movimento (
    movimento_key  BIGINT IDENTITY NOT NULL PRIMARY KEY,
    data_key       INT            NOT NULL REFERENCES dw.dim_calendario,
    produto_key    INT            NOT NULL REFERENCES dw.dim_produto,
    tipo_movimento NVARCHAR(25)   NOT NULL,
    quantidade     INT            NOT NULL,   -- entradas positivas, saídas negativas
    valor          DECIMAL(14, 2) NOT NULL    -- a custo
);

CREATE TABLE dw.fato_quadro_mensal (
    competencia_key         INT NOT NULL REFERENCES dw.dim_calendario,
    funcionario_key         INT NOT NULL REFERENCES dw.dim_funcionario,
    cc_key                  INT NOT NULL REFERENCES dw.dim_centro_custo,
    filial_key              INT NOT NULL REFERENCES dw.dim_filial,
    ativo_inicio_mes        BIT NOT NULL,
    ativo_fim_mes           BIT NOT NULL,
    admitido_no_mes         BIT NOT NULL,
    desligado_no_mes        BIT NOT NULL,
    desligamento_voluntario BIT NOT NULL,
    PRIMARY KEY (competencia_key, funcionario_key)
);
GO
