# Catálogo de indicadores

Gerado por [`python/gerar_catalogo.py`](../python/gerar_catalogo.py) a partir dos modelos semânticos em [`powerbi/`](../powerbi). Não edite à mão: a definição de cada indicador é a descrição da medida no modelo (linha `///` no TMDL, ou a propriedade Descrição no Power BI Desktop), que é também o que aparece ao passar o mouse sobre a medida no Power BI. Para mudar uma definição, mude no modelo e gere de novo.

A coluna **2025** traz o valor das medidas que foram conferidas contra as views de conferência do SQL (`dw.vw_conferencia_*`). As medidas de formatação, ocultas, ficam de fora. [Versão com busca](https://lucasgama.vercel.app/indicadores.html) no portfólio.

| Painel | Indicadores | Conferidos com o SQL |
|---|---:|---:|
| Financeiro | 55 | 24 |
| People Analytics | 33 | 10 |
| Compras e Estoque | 28 | 11 |
| Comercial | 24 | 14 |
| **Total** | **140** | **59** |

## Nomes repetidos entre modelos

O mesmo nome em mais de um modelo pede atenção: se o cálculo é diferente, o nome deveria deixar isso claro.

- **Devoluções** (fórmulas diferentes)
  - Financeiro: Devoluções de vendas (conta 3.02 da DRE). `CALCULATE(SUM(DRE[Valor]), Conta[Código Conta] = "3.02")`
  - Comercial: Notas de devolução de clientes, em valor positivo. Bate com a conta 3.02 da DRE. `CALCULATE(-SUM(Venda[Valor Líquido]), Venda[Tipo de Operação] = "DEVOLUCAO")`
- **Receita Líquida** (fórmulas diferentes)
  - Financeiro: Receita bruta menos devoluções e impostos sobre vendas. `[Receita Bruta] - [Devoluções] - [Impostos sobre Vendas]`
  - Compras e Estoque: Vendas depois do desconto e das devoluções, antes dos impostos (base da curva ABC). Não é a receita líquida da DRE, que também desconta os impostos. `SUM(Venda[Receita Líquida])`

## Financeiro

### 1. DRE

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Receita Bruta | Receita das notas faturadas, já sem o desconto comercial. | `CALCULATE(SUM(DRE[Valor]), Conta[Código Conta] = "3.01")` | `dw.dim_conta`, `dw.fato_dre` | R$ 62.772.565 |
| Devoluções | Devoluções de vendas (conta 3.02 da DRE). | `CALCULATE(SUM(DRE[Valor]), Conta[Código Conta] = "3.02")` | `dw.dim_conta`, `dw.fato_dre` |  |
| Impostos sobre Vendas | ICMS e PIS/COFINS apurados no mês (regime simplificado do projeto). | `CALCULATE(SUM(DRE[Valor]), Conta[Código Conta] = "3.03")` | `dw.dim_conta`, `dw.fato_dre` |  |
| Receita Líquida | Receita bruta menos devoluções e impostos sobre vendas. | `[Receita Bruta] - [Devoluções] - [Impostos sobre Vendas]` | `dw.dim_conta`, `dw.fato_dre` | R$ 53.670.306 |
| CMV | Custo médio das mercadorias vendidas (líquido das devoluções). | `CALCULATE(SUM(DRE[Valor]), Conta[Grupo DRE] = "CMV")` | `dw.dim_conta`, `dw.fato_dre` | R$ 40.890.111 |
| Lucro Bruto | Receita líquida menos o custo das mercadorias vendidas (CMV). | `[Receita Líquida] - [CMV]` | `dw.dim_conta`, `dw.fato_dre` | R$ 12.780.195 |
| Margem Bruta % | Lucro bruto ÷ receita líquida. | `DIVIDE([Lucro Bruto], [Receita Líquida])` | `dw.dim_conta`, `dw.fato_dre` | 23,8% |
| Despesas com Pessoal | Salários, encargos e benefícios (grupo Despesas com pessoal da DRE). | `CALCULATE(SUM(DRE[Valor]), Conta[Grupo DRE] = "Despesas com pessoal")` | `dw.dim_conta`, `dw.fato_dre` |  |
| Despesas Operacionais | Pessoal + administrativas + logísticas + comerciais. | `CALCULATE(SUM(DRE[Valor]), Conta[Ordem DRE] IN {4, 5, 6, 7})` | `dw.dim_conta`, `dw.fato_dre` | R$ 10.455.678 |
| Resultado Operacional | Lucro bruto menos as despesas operacionais. | `[Lucro Bruto] - [Despesas Operacionais]` | `dw.dim_conta`, `dw.fato_dre` |  |
| Resultado Financeiro | Tarifas bancárias e juros da DRE; negativo quando é despesa. | `-CALCULATE(SUM(DRE[Valor]), Conta[Grupo DRE] = "Resultado financeiro")` | `dw.dim_conta`, `dw.fato_dre` |  |
| Resultado Líquido | Soma de todas as contas da DRE com sinal: receita menos deduções, CMV e despesas. | `SUM(DRE[Valor Resultado])` | `dw.fato_dre` | R$ 2.234.353 |
| Margem Líquida % | Resultado líquido ÷ receita líquida. | `DIVIDE([Resultado Líquido], [Receita Líquida])` | `dw.dim_conta`, `dw.fato_dre` | 4,2% |
| Realizado | Valor da DRE com sinal, para usar numa matriz com Grupo DRE e Conta nas linhas. | `SUM(DRE[Valor Resultado])` | `dw.fato_dre` |  |
| % da Receita Líquida | Análise vertical: peso de cada linha da DRE sobre a receita líquida. | `DIVIDE([Realizado], CALCULATE([Receita Líquida], REMOVEFILTERS(Conta)))` | `dw.dim_conta`, `dw.fato_dre` |  |

### 2. Orçamento

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Orçado | Orçamento com o sinal da conta (receita positiva, custos e despesas negativos). Fica em branco quando há filtro de filial, porque o orçamento não é aberto por filial. | `IF(     ISFILTERED(Filial),     BLANK(),     SUMX('Orçamento', 'Orçamento'[Valor] * RELATED(Conta[Sinal])) )` | `dw.dim_conta`, `dw.dim_filial`, `dw.fato_orcamento` |  |
| Desvio | Realizado - Orçado. Negativo = pior que o orçado (vale para receitas e para despesas). | `IF(ISBLANK([Orçado]), BLANK(), [Realizado] - [Orçado])` | `dw.dim_conta`, `dw.fato_dre`, `dw.dim_filial`, `dw.fato_orcamento` |  |
| Desvio % | Desvio ÷ orçado. Divide pelo orçado em valor absoluto para o sinal continuar dizendo se ficou acima ou abaixo. | `DIVIDE([Desvio], ABS([Orçado]))` | `dw.dim_conta`, `dw.fato_dre`, `dw.dim_filial`, `dw.fato_orcamento` |  |
| Receita Orçada | Receita bruta orçada (conta 3.01). | `CALCULATE([Orçado], Conta[Código Conta] = "3.01")` | `dw.dim_conta`, `dw.dim_filial`, `dw.fato_orcamento` | R$ 63.727.000 |
| Atingimento da Receita % | Receita bruta realizada ÷ receita orçada. | `DIVIDE([Receita Bruta], [Receita Orçada])` | `dw.dim_conta`, `dw.fato_dre`, `dw.dim_filial`, `dw.fato_orcamento` | 98,5% |
| Resultado Orçado | Resultado líquido do orçamento: todas as contas orçadas, com o sinal da DRE. | `CALCULATE([Orçado], REMOVEFILTERS(Conta))` | `dw.dim_conta`, `dw.dim_filial`, `dw.fato_orcamento` | R$ 4.113.200 |
| Desvio do Resultado | Resultado líquido realizado menos o orçado; vazio quando não há orçamento no período. | `IF(ISBLANK([Resultado Orçado]), BLANK(), [Resultado Líquido] - [Resultado Orçado])` | `dw.dim_conta`, `dw.fato_dre`, `dw.dim_filial`, `dw.fato_orcamento` | R$ −1.878.847 |
| Desvio das Despesas | Desvio só das contas de despesa (pessoal, administrativas, logísticas e comerciais). | `CALCULATE([Desvio], KEEPFILTERS(Conta[Ordem DRE] IN {4, 5, 6, 7}))` | `dw.dim_conta`, `dw.fato_dre`, `dw.dim_filial`, `dw.fato_orcamento` |  |

### 3. Contas a Receber

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Carteira em Aberto | Títulos não pagos na data de corte (31/12/2025). Ignora o filtro de datas. | `CALCULATE(     SUM('Contas a Receber'[Valor]),     'Contas a Receber'[Status] <> "PAGO",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` | R$ 5.277.582 |
| Vencido | Títulos a receber vencidos e não pagos na data de corte (fotografia: ignora o filtro de data). | `CALCULATE(     SUM('Contas a Receber'[Valor]),     'Contas a Receber'[Status] = "VENCIDO",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` | R$ 537.896 |
| A Vencer | Títulos a receber ainda no prazo na data de corte. | `CALCULATE(     SUM('Contas a Receber'[Valor]),     'Contas a Receber'[Status] = "A VENCER",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` |  |
| Vencido há Mais de 90 Dias | Títulos a receber vencidos há mais de 90 dias na data de corte. | `CALCULATE(     SUM('Contas a Receber'[Valor]),     'Contas a Receber'[Faixa de Aging] = "Mais de 90 dias",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` | R$ 258.573 |
| Inadimplência % | Vencido ÷ carteira em aberto, na data de corte. | `DIVIDE([Vencido], [Carteira em Aberto])` | `dw.fato_conta_receber` | 10,2% |
| Clientes Inadimplentes | Clientes com pelo menos um título vencido na data de corte. | `CALCULATE(     DISTINCTCOUNT('Contas a Receber'[cliente_key]),     'Contas a Receber'[Status] = "VENCIDO",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` | 78 |
| Valor a Receber | Valor do contas a receber por mês de vencimento (o calendário filtra pelo vencimento). | `SUM('Contas a Receber'[Valor])` | `dw.fato_conta_receber` |  |
| Recebido | Entradas de caixa: valor efetivamente recebido, pela data do pagamento. | `CALCULATE(     SUM('Contas a Receber'[Valor Pago]),     USERELATIONSHIP('Contas a Receber'[pagamento_key], 'Calendário'[data_key]) )` | `dw.fato_conta_receber` | R$ 63.136.476 |
| Juros e Multas Recebidos | Juros e multas pagos pelos clientes, pela data do pagamento. | `CALCULATE(     SUM('Contas a Receber'[Juros e Multa]),     USERELATIONSHIP('Contas a Receber'[pagamento_key], 'Calendário'[data_key]) )` | `dw.fato_conta_receber` |  |
| PMR (dias) | Prazo médio de recebimento: dias entre emissão e pagamento, ponderado pelo valor, títulos pagos no período. | `CALCULATE(     DIVIDE(         SUMX('Contas a Receber', 'Contas a Receber'[Valor] * 'Contas a Receber'[Prazo Real (dias)]),         SUM('Contas a Receber'[Valor])     ),     USERELATIONSHIP('Contas a Receber'[pagamento_key], 'Calendário'[data_key]),     NOT ISBLANK('Contas a Receber'[Prazo Real (dias)]) )` | `dw.fato_conta_receber` | 28,0 |
| Prazo Médio Concedido (dias) | Prazo combinado com o cliente (emissão até vencimento), mesma base de títulos do PMR. | `CALCULATE(     DIVIDE(         SUMX('Contas a Receber', 'Contas a Receber'[Valor] * 'Contas a Receber'[Prazo Concedido (dias)]),         SUM('Contas a Receber'[Valor])     ),     USERELATIONSHIP('Contas a Receber'[pagamento_key], 'Calendário'[data_key]),     NOT ISBLANK('Contas a Receber'[Prazo Real (dias)]) )` | `dw.fato_conta_receber` | 26,6 |
| Atraso Médio no Recebimento (dias) | Quantos dias, em média ponderada, os clientes pagam depois do combinado. | `[PMR (dias)] - [Prazo Médio Concedido (dias)]` | `dw.fato_conta_receber` |  |
| Maior Atraso (dias) | Maior atraso entre os títulos vencidos na data de corte, em dias. | `CALCULATE(     MAX('Contas a Receber'[Dias de Atraso]),     'Contas a Receber'[Status] = "VENCIDO",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_receber` |  |

### 4. Caixa e Contas a Pagar

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Pago | Saídas de caixa: valor efetivamente pago, pela data do pagamento (inclui compra de mercadoria). | `CALCULATE(     SUM('Contas a Pagar'[Valor Pago]),     USERELATIONSHIP('Contas a Pagar'[pagamento_key], 'Calendário'[data_key]) )` | `dw.fato_conta_pagar` | R$ 60.925.343 |
| Geração de Caixa | Recebido menos pago no período, pelo caixa. | `[Recebido] - [Pago]` | `dw.fato_conta_pagar`, `dw.fato_conta_receber` | R$ 2.211.133 |
| Geração de Caixa Acumulada | Soma da geração de caixa desde jan/2024 até a última data do contexto (não inclui o saldo bancário inicial). Fica em branco depois da data de corte, para a linha não seguir reta pelos meses sem dados. | `VAR UltimaData = MAX('Calendário'[Data]) RETURN     IF(         MIN('Calendário'[Data]) > [Data de Corte],         BLANK(),         CALCULATE(             [Geração de Caixa],             REMOVEFILTERS('Calendário'),             'Calendário'[Data] <= UltimaData         )     )` | `dw.fato_conta_pagar`, `dw.fato_conta_receber` |  |
| A Pagar em Aberto | Títulos a pagar ainda não pagos na data de corte. | `CALCULATE(     SUM('Contas a Pagar'[Valor]),     'Contas a Pagar'[Status] <> "PAGO",     REMOVEFILTERS('Calendário') )` | `dw.fato_conta_pagar` | R$ 5.981.087 |
| Valor a Pagar | Valor do contas a pagar por mês de vencimento (o calendário filtra pelo vencimento). | `SUM('Contas a Pagar'[Valor])` | `dw.fato_conta_pagar` |  |
| Saldo Projetado | Projeção: o que entra menos o que sai nos títulos ainda abertos, por mês de vencimento. | `CALCULATE([Valor a Receber], 'Contas a Receber'[Status] <> "PAGO")     - CALCULATE([Valor a Pagar], 'Contas a Pagar'[Status] <> "PAGO")` | `dw.fato_conta_pagar`, `dw.fato_conta_receber` |  |
| Juros e Multas Pagos | Juros e multas pagos a fornecedores, pela data do pagamento. | `CALCULATE(     SUM('Contas a Pagar'[Juros e Multa]),     USERELATIONSHIP('Contas a Pagar'[pagamento_key], 'Calendário'[data_key]) )` | `dw.fato_conta_pagar` |  |
| Pagamentos em Atraso % | Percentual dos títulos pagos no período que foram pagos depois do vencimento. | `CALCULATE(     DIVIDE(         COUNTROWS(FILTER('Contas a Pagar', 'Contas a Pagar'[Dias de Atraso] > 0)),         COUNTROWS('Contas a Pagar')     ),     USERELATIONSHIP('Contas a Pagar'[pagamento_key], 'Calendário'[data_key]),     'Contas a Pagar'[Status] = "PAGO" )` | `dw.fato_conta_pagar` |  |
| PMP (dias) | Prazo médio de pagamento a fornecedores de mercadoria (emissão até pagamento, ponderado pelo valor). | `CALCULATE(     DIVIDE(         SUMX('Contas a Pagar', 'Contas a Pagar'[Valor] * 'Contas a Pagar'[Prazo Real (dias)]),         SUM('Contas a Pagar'[Valor])     ),     USERELATIONSHIP('Contas a Pagar'[pagamento_key], 'Calendário'[data_key]),     NOT ISBLANK('Contas a Pagar'[Prazo Real (dias)]),     Conta[Código Conta] = "1.05" )` | `dw.dim_conta`, `dw.fato_conta_pagar` | 30,7 |
| PMR - PMP (dias) | Positivo = a empresa recebe dos clientes depois de pagar os fornecedores e precisa financiar a diferença. | `[PMR (dias)] - [PMP (dias)]` | `dw.dim_conta`, `dw.fato_conta_pagar`, `dw.fato_conta_receber` |  |
| A Receber (projeção) | Títulos a receber ainda abertos, por mês de vencimento depois da data de corte. | `CALCULATE(     [Valor a Receber],     'Contas a Receber'[Status] <> "PAGO",     KEEPFILTERS('Calendário'[Data] > DATE(2025, 12, 31)) )` | `dw.fato_conta_receber` |  |
| A Pagar (projeção) | Títulos a pagar ainda abertos, por mês de vencimento depois da data de corte. | `CALCULATE(     [Valor a Pagar],     'Contas a Pagar'[Status] <> "PAGO",     KEEPFILTERS('Calendário'[Data] > DATE(2025, 12, 31)) )` | `dw.fato_conta_pagar` |  |

### 5. Comparativos

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Receita Líquida Ano Anterior | Receita líquida no mesmo período do ano anterior. | `CALCULATE([Receita Líquida], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.dim_conta`, `dw.fato_dre` |  |
| Receita Líquida vs Ano Anterior % | Variação da receita líquida contra o mesmo período do ano anterior. | `DIVIDE([Receita Líquida] - [Receita Líquida Ano Anterior], [Receita Líquida Ano Anterior])` | `dw.dim_conta`, `dw.fato_dre` |  |
| Resultado Líquido Ano Anterior | Resultado líquido no mesmo período do ano anterior. | `CALCULATE([Resultado Líquido], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.fato_dre` |  |
| Margem Líquida Ano Anterior % | Margem líquida no mesmo período do ano anterior. | `CALCULATE([Margem Líquida %], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.dim_conta`, `dw.fato_dre` |  |
| Margem Líquida vs Ano Anterior (p.p.) | Variação da margem líquida em pontos percentuais. | `([Margem Líquida %] - [Margem Líquida Ano Anterior %]) * 100` | `dw.dim_conta`, `dw.fato_dre` |  |
| Resultado Acumulado no Ano | Resultado líquido acumulado de janeiro até o fim do período filtrado. | `TOTALYTD([Resultado Líquido], 'Calendário'[Data])` | `dw.fato_dre` |  |
| Data de Corte | Data da fotografia de títulos em aberto, vencidos e aging: 31/12/2025. | `DATE(2025, 12, 31)` | — |  |


## People Analytics

### 1. Quadro

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Headcount | Pessoas ativas no fim do último mês do período selecionado. | `VAR UltimoMes = MAX('Quadro Mensal'[competencia_key]) RETURN CALCULATE(SUM('Quadro Mensal'[Ativo no Fim do Mês]), 'Quadro Mensal'[competencia_key] = UltimoMes)` | `dw.fato_quadro_mensal` | 91 |
| Headcount Médio | Média mensal de (headcount do início + headcount do fim) / 2. Base da taxa de rotatividade. | `AVERAGEX(     VALUES('Quadro Mensal'[competencia_key]),     CALCULATE(SUM('Quadro Mensal'[Ativo no Início do Mês]) + SUM('Quadro Mensal'[Ativo no Fim do Mês])) / 2 )` | `dw.fato_quadro_mensal` | 90,5 |
| Admissões | Admissões no período. | `SUM('Quadro Mensal'[Admitido no Mês])` | `dw.fato_quadro_mensal` | 42 |
| Desligamentos | Desligamentos no período, voluntários e involuntários. | `SUM('Quadro Mensal'[Desligado no Mês])` | `dw.fato_quadro_mensal` | 41 |
| Saldo de Contratações | Admissões menos desligamentos. | `[Admissões] - [Desligamentos]` | `dw.fato_quadro_mensal` |  |

### 2. Rotatividade

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Desligamentos por Motivo | Desligamentos para gráficos por motivo: esconde a categoria vazia (funcionários ativos não têm motivo). | `IF(ISBLANK(SELECTEDVALUE('Funcionário'[Motivo do Desligamento])), BLANK(), [Desligamentos])` | `dw.dim_funcionario`, `dw.fato_quadro_mensal` |  |
| Desligamentos Voluntários | Desligamentos a pedido do funcionário. | `SUM('Quadro Mensal'[Desligamento Voluntário])` | `dw.fato_quadro_mensal` |  |
| Turnover % | Desligamentos ÷ headcount médio do período. Com um ano selecionado, é a rotatividade anual. | `DIVIDE([Desligamentos], [Headcount Médio])` | `dw.fato_quadro_mensal` | 45,3% |
| Turnover Voluntário % | Só pedidos de demissão: mede quanto a empresa perde gente que queria manter. | `DIVIDE([Desligamentos Voluntários], [Headcount Médio])` | `dw.fato_quadro_mensal` | 22,1% |
| % Voluntário dos Desligamentos | Fatia dos desligamentos que foi a pedido do funcionário. | `DIVIDE([Desligamentos Voluntários], [Desligamentos])` | `dw.fato_quadro_mensal` |  |
| Desligamentos na Experiência | Saídas com menos de 3 meses de casa (período de experiência). | `CALCULATE([Desligamentos], KEEPFILTERS('Funcionário'[Tempo de Casa (meses)] < 3))` | `dw.dim_funcionario`, `dw.fato_quadro_mensal` | 10 |
| % Saídas na Experiência | Fatia dos desligamentos que aconteceu no contrato de experiência. | `DIVIDE([Desligamentos na Experiência], [Desligamentos])` | `dw.dim_funcionario`, `dw.fato_quadro_mensal` |  |
| Desligamentos no 1º Ano | Desligamentos de quem tinha menos de 12 meses de casa. | `CALCULATE([Desligamentos], KEEPFILTERS('Funcionário'[Tempo de Casa (meses)] < 12))` | `dw.dim_funcionario`, `dw.fato_quadro_mensal` |  |
| % Saídas no 1º Ano | Fatia dos desligamentos que aconteceu antes de um ano de casa. | `DIVIDE([Desligamentos no 1º Ano], [Desligamentos])` | `dw.dim_funcionario`, `dw.fato_quadro_mensal` |  |

### 3. Absenteísmo e Horas Extras

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Dias Previstos | Dias de trabalho previstos na escala: a base do absenteísmo. | `SUM(Ponto[Dias Previstos])` | `dw.fato_ponto` |  |
| Faltas | Dias de falta, sem contar os atestados. | `SUM(Ponto[Faltas])` | `dw.fato_ponto` |  |
| Dias de Atestado | Dias de afastamento com atestado médico. | `SUM(Ponto[Dias de Atestado])` | `dw.fato_ponto` |  |
| Absenteísmo % | (Faltas + dias de atestado) ÷ dias úteis previstos. | `DIVIDE([Faltas] + [Dias de Atestado], [Dias Previstos])` | `dw.fato_ponto` | 2,9% |
| Horas Extras | Horas extras registradas no ponto. | `SUM(Ponto[Horas Extras])` | `dw.fato_ponto` | 11.300 |
| Horas Extras por Pessoa (mês) | Horas extras por funcionário em cada mês trabalhado. | `DIVIDE([Horas Extras], COUNTROWS(Ponto))` | `dw.fato_ponto` |  |
| Faltas por Pessoa (mês) | Faltas por funcionário por mês trabalhado (cada linha do ponto é um funcionário em um mês). | `DIVIDE([Faltas], COUNTROWS(Ponto))` | `dw.fato_ponto` |  |
| Faltas por Mês: Quem Saiu | Faltas por mês de quem já saiu da empresa: o sinal de alerta antes do desligamento. | `CALCULATE([Faltas por Pessoa (mês)], 'Funcionário'[Situação] = "Desligado")` | `dw.dim_funcionario`, `dw.fato_ponto` |  |
| Faltas por Mês: Quem Ficou | Faltas por pessoa por mês de quem está ativo hoje. | `CALCULATE([Faltas por Pessoa (mês)], 'Funcionário'[Situação] = "Ativo")` | `dw.dim_funcionario`, `dw.fato_ponto` |  |
| Quem Saiu Faltava a Mais % | Quanto a mais quem saiu faltava por mês, em relação a quem ficou. | `DIVIDE([Faltas por Mês: Quem Saiu] - [Faltas por Mês: Quem Ficou], [Faltas por Mês: Quem Ficou])` | `dw.dim_funcionario`, `dw.fato_ponto` |  |
| Absenteísmo: Quem Saiu | Absenteísmo de quem já foi desligado. | `CALCULATE([Absenteísmo %], 'Funcionário'[Situação] = "Desligado")` | `dw.dim_funcionario`, `dw.fato_ponto` |  |
| Absenteísmo: Quem Ficou | Absenteísmo de quem está ativo hoje. | `CALCULATE([Absenteísmo %], 'Funcionário'[Situação] = "Ativo")` | `dw.dim_funcionario`, `dw.fato_ponto` |  |

### 4. Custo

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Custo de Pessoal | Salários, encargos e benefícios (competência). | `SUM('Custo de Pessoal'[Valor])` | `dw.vw_custo_pessoal` | R$ 8.074.876 |
| Custo Médio por Pessoa (mês) | Custo de pessoal ÷ soma do headcount médio de cada mês. | `DIVIDE(     [Custo de Pessoal],     SUMX(         VALUES('Quadro Mensal'[competencia_key]),         CALCULATE(SUM('Quadro Mensal'[Ativo no Início do Mês]) + SUM('Quadro Mensal'[Ativo no Fim do Mês])) / 2     ) )` | `dw.vw_custo_pessoal`, `dw.fato_quadro_mensal` |  |
| Salário Médio (ativos) | Salário médio atual dos funcionários ativos. | `CALCULATE(AVERAGE('Funcionário'[Salário Atual]), 'Funcionário'[Situação] = "Ativo")` | `dw.dim_funcionario` |  |

### 5. Comparativos

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Turnover Ano Anterior % | Turnover no mesmo período do ano anterior. | `CALCULATE([Turnover %], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.fato_quadro_mensal` |  |
| Turnover vs Ano Anterior (p.p.) | Variação da rotatividade em pontos percentuais. Positivo = a empresa está perdendo mais gente. | `IF(ISBLANK([Turnover Ano Anterior %]), BLANK(), ([Turnover %] - [Turnover Ano Anterior %]) * 100)` | `dw.fato_quadro_mensal` |  |
| Custo de Pessoal Ano Anterior | Custo de pessoal no mesmo período do ano anterior. | `CALCULATE([Custo de Pessoal], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.vw_custo_pessoal` |  |
| Custo de Pessoal vs Ano Anterior % | Variação do custo de pessoal contra o mesmo período do ano anterior. | `DIVIDE([Custo de Pessoal] - [Custo de Pessoal Ano Anterior], [Custo de Pessoal Ano Anterior])` | `dw.vw_custo_pessoal` |  |


## Compras e Estoque

### 1. Compras

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Valor Comprado | Valor dos itens dos pedidos de compra, pela data do pedido. | `SUM(Compra[Valor Total])` | `dw.fato_compra` | R$ 40.935.841 |
| Pedidos de Compra | Pedidos de compra distintos, pela data do pedido. | `DISTINCTCOUNT(Compra[Pedido de Compra])` | `dw.fato_compra` | 924 |
| Pedidos Entregues | Pedidos de compra que já têm data de entrega. | `CALCULATE(DISTINCTCOUNT(Compra[Pedido de Compra]), NOT ISBLANK(Compra[entrega_real_key]))` | `dw.fato_compra` |  |
| Entregas no Prazo % | % dos pedidos entregues até a data prometida. Medido por pedido: todos os itens de um pedido chegam juntos. | `VAR Pedidos =     ADDCOLUMNS(         CALCULATETABLE(VALUES(Compra[Pedido de Compra]), NOT ISBLANK(Compra[entrega_real_key])),         "@noPrazo", CALCULATE(MAX(Compra[Entregue no Prazo]))     ) RETURN DIVIDE(COUNTROWS(FILTER(Pedidos, [@noPrazo] = 1)), COUNTROWS(Pedidos))` | `dw.fato_compra` | 73,8% |
| Atraso Médio quando Atrasa (dias) | Média de dias de atraso considerando só os pedidos que atrasaram. | `VAR Pedidos =     ADDCOLUMNS(         CALCULATETABLE(VALUES(Compra[Pedido de Compra]), NOT ISBLANK(Compra[entrega_real_key])),         "@atraso", CALCULATE(MAX(Compra[Dias de Atraso na Entrega]))     ) RETURN AVERAGEX(FILTER(Pedidos, [@atraso] > 0), [@atraso])` | `dw.fato_compra` | 2,7 |

### 2. Estoque

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Estoque (R$) | Valor do estoque (a custo) no último dia do período, limitado à data de corte. | `VAR Ultima = MIN(MAX('Calendário'[Data]), DATE(2025, 12, 31)) RETURN     IF(         MIN('Calendário'[Data]) > DATE(2025, 12, 31),         BLANK(),         CALCULATE(SUM('Movimento de Estoque'[Valor]), REMOVEFILTERS('Calendário'), 'Calendário'[Data] <= Ultima)     )` | `dw.fato_estoque_movimento` | R$ 3.188.982 |
| Estoque (unidades) | Saldo de estoque em unidades no último dia do período, limitado à data de corte (31/12/2025). | `VAR Ultima = MIN(MAX('Calendário'[Data]), DATE(2025, 12, 31)) RETURN     IF(         MIN('Calendário'[Data]) > DATE(2025, 12, 31),         BLANK(),         CALCULATE(SUM('Movimento de Estoque'[Quantidade]), REMOVEFILTERS('Calendário'), 'Calendário'[Data] <= Ultima)     )` | `dw.fato_estoque_movimento` |  |
| CMV das Vendas | Custo das mercadorias que saíram por venda, líquido das devoluções. | `-CALCULATE(     SUM('Movimento de Estoque'[Valor]),     'Movimento de Estoque'[Tipo de Movimento] IN {"Saída por venda", "Devolução de cliente"} )` | `dw.fato_estoque_movimento` | R$ 40.890.111 |
| Estoque Médio (R$) | Média do valor do estoque no fim de cada mês do período. | `AVERAGEX(     FILTER(         VALUES('Calendário'[Primeiro Dia do Mês]),         'Calendário'[Primeiro Dia do Mês] >= DATE(2024, 1, 1) && 'Calendário'[Primeiro Dia do Mês] <= DATE(2025, 12, 1)     ),     CALCULATE([Estoque (R$)]) )` | `dw.fato_estoque_movimento` | R$ 2.587.720 |
| Giro de Estoque | Quantas vezes o estoque "girou" no período: CMV ÷ estoque médio. | `DIVIDE([CMV das Vendas], [Estoque Médio (R$)])` | `dw.fato_estoque_movimento` | 15,8 |
| Cobertura de Estoque (dias) | Quantos dias de venda o estoque do fim do período cobre, pelo ritmo médio do período. | `VAR Dias =     CALCULATE(         COUNTROWS('Calendário'),         KEEPFILTERS('Calendário'[Data] >= DATE(2024, 1, 1) && 'Calendário'[Data] <= DATE(2025, 12, 31))     ) RETURN DIVIDE([Estoque (R$)], DIVIDE([CMV das Vendas], Dias))` | `dw.fato_estoque_movimento` |  |

### 3. Nível de Serviço

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Unidades Pedidas | Unidades que os clientes pediram nas notas de venda. | `CALCULATE(SUM(Venda[Qtd Pedida]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` |  |
| Unidades Atendidas | Unidades faturadas nas notas de venda. | `CALCULATE(SUM(Venda[Qtd Faturada]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` |  |
| Nível de Serviço % | Unidades faturadas ÷ unidades que os clientes pediram (fill rate). | `DIVIDE([Unidades Atendidas], [Unidades Pedidas])` | `dw.fato_venda` | 98,1% |
| Unidades Não Atendidas | Unidades pedidas que não foram faturadas por falta de estoque. | `[Unidades Pedidas] - [Unidades Atendidas]` | `dw.fato_venda` | 10.366 |
| Ruptura % | Unidades não atendidas ÷ unidades pedidas. É o complemento do nível de serviço. | `DIVIDE([Unidades Não Atendidas], [Unidades Pedidas])` | `dw.fato_venda` |  |
| Venda Perdida por Ruptura | Receita que deixou de entrar porque faltou produto: unidades não atendidas × preço com desconto. | `CALCULATE(     SUMX(Venda, (Venda[Qtd Pedida] - Venda[Qtd Faturada]) * Venda[Preço Unitário] * (1 - Venda[Desconto %] / 100)),     Venda[Tipo de Operação] = "VENDA" )` | `dw.fato_venda` | R$ 917.902 |
| Produtos com Ruptura | Produtos com pelo menos uma unidade não atendida no período. | `COUNTROWS(FILTER(VALUES(Produto[Código Produto]), [Unidades Não Atendidas] > 0))` | `dw.dim_produto`, `dw.fato_venda` |  |

### 4. Curva ABC

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Receita Líquida | Vendas depois do desconto e das devoluções, antes dos impostos (base da curva ABC). Não é a receita líquida da DRE, que também desconta os impostos. | `SUM(Venda[Receita Líquida])` | `dw.fato_venda` |  |
| Produtos | Produtos do cadastro dentro do filtro. | `COUNTROWS(Produto)` | `dw.dim_produto` |  |
| % dos Produtos | Fatia dos produtos que está em cada classe (use com Produto[Classe ABC]). | `DIVIDE(COUNTROWS(Produto), CALCULATE(COUNTROWS(Produto), REMOVEFILTERS(Produto[Classe ABC])))` | `dw.dim_produto` |  |
| % da Receita | Fatia da receita que cada classe representa (use com Produto[Classe ABC]). | `DIVIDE([Receita Líquida], CALCULATE([Receita Líquida], REMOVEFILTERS(Produto[Classe ABC])))` | `dw.dim_produto`, `dw.fato_venda` |  |
| Participação na Receita | Receita líquida do produto ÷ receita líquida de todos os produtos. | `DIVIDE([Receita Líquida], CALCULATE([Receita Líquida], REMOVEFILTERS(Produto)))` | `dw.dim_produto`, `dw.fato_venda` |  |
| Produtos Classe A | Produtos na classe A da curva ABC: os que somam os primeiros 80% da receita. | `CALCULATE([Produtos], Produto[Classe ABC] = "A")` | `dw.dim_produto` |  |
| % dos Produtos na Classe A | Fatia dos produtos que está na classe A. | `CALCULATE([% dos Produtos], Produto[Classe ABC] = "A")` | `dw.dim_produto` |  |
| % da Receita na Classe A | Fatia da receita que vem dos produtos da classe A. | `CALCULATE([% da Receita], Produto[Classe ABC] = "A")` | `dw.dim_produto`, `dw.fato_venda` |  |

### 5. Comparativos

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Valor Comprado Ano Anterior | Valor comprado no mesmo período do ano anterior. | `CALCULATE([Valor Comprado], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.fato_compra` |  |
| Valor Comprado vs Ano Anterior % | Variação do valor comprado contra o mesmo período do ano anterior. | `DIVIDE([Valor Comprado] - [Valor Comprado Ano Anterior], [Valor Comprado Ano Anterior])` | `dw.fato_compra` |  |


## Comercial

### 1. Vendas

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Faturamento | Vendas já com desconto, antes das devoluções e dos impostos. É a receita bruta da DRE (conta 3.01). | `CALCULATE(SUM(Venda[Valor Líquido]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` | R$ 62.772.565 |
| Valor de Tabela | Preço de tabela das vendas, antes do desconto: faturamento + descontos concedidos. | `CALCULATE(SUM(Venda[Valor de Tabela]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` |  |
| Descontos Concedidos | Desconto comercial dado nas notas de venda. | `CALCULATE(SUM(Venda[Valor do Desconto]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` | R$ 2.505.856 |
| Desconto Médio % | Descontos concedidos ÷ valor de tabela das vendas. | `DIVIDE([Descontos Concedidos], [Valor de Tabela])` | `dw.fato_venda` | 3,8% |
| Devoluções | Notas de devolução de clientes, em valor positivo. Bate com a conta 3.02 da DRE. | `CALCULATE(-SUM(Venda[Valor Líquido]), Venda[Tipo de Operação] = "DEVOLUCAO")` | `dw.fato_venda` | R$ 256.194 |
| Venda Líquida | Faturamento menos devoluções. | `SUM(Venda[Valor Líquido])` | `dw.fato_venda` | R$ 62.516.372 |
| Custo das Vendas | Custo das vendas menos o custo das devoluções. É o CMV da DRE. | `SUM(Venda[Custo Total])` | `dw.fato_venda` | R$ 40.890.111 |
| Margem Comercial % | Antes dos impostos sobre vendas, por isso é maior que a margem bruta da DRE. | `DIVIDE([Venda Líquida] - [Custo das Vendas], [Venda Líquida])` | `dw.fato_venda` | 34,6% |
| Notas Fiscais | Notas de venda distintas. A coluna Nota junta filial e número, porque a numeração é por filial. | `CALCULATE(DISTINCTCOUNT(Venda[Nota]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` | 11.891 |
| Ticket Médio | Faturamento médio por nota fiscal de venda. | `DIVIDE([Faturamento], [Notas Fiscais])` | `dw.fato_venda` | R$ 5.279 |

### 2. Clientes

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Clientes que Compraram | Clientes distintos com pelo menos uma nota de venda no período. | `CALCULATE(DISTINCTCOUNT(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA")` | `dw.fato_venda` | 371 |
| Faturamento por Cliente | Faturamento ÷ clientes que compraram no período. | `DIVIDE([Faturamento], [Clientes que Compraram])` | `dw.fato_venda` |  |
| Clientes Novos | Compraram no período e não no mesmo período do ano anterior. Em branco no primeiro ano da série. | `VAR Agora = CALCULATETABLE(VALUES(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA") VAR Antes = CALCULATETABLE(VALUES(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA", SAMEPERIODLASTYEAR('Calendário'[Data])) RETURN IF(ISEMPTY(Antes), BLANK(), COUNTROWS(EXCEPT(Agora, Antes)))` | `dw.fato_venda` | 34 |
| Clientes Perdidos | Compraram no mesmo período do ano anterior e não no período. Em branco no primeiro ano da série. | `VAR Agora = CALCULATETABLE(VALUES(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA") VAR Antes = CALCULATETABLE(VALUES(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA", SAMEPERIODLASTYEAR('Calendário'[Data])) RETURN IF(ISEMPTY(Antes), BLANK(), COUNTROWS(EXCEPT(Antes, Agora)))` | `dw.fato_venda` | 49 |
| Faturamento dos 20% Maiores % | Fatia do faturamento que vem do primeiro quinto do ranking de clientes (como NTILE(5) no SQL). | `VAR Clientes = ADDCOLUMNS(CALCULATETABLE(VALUES(Venda[cliente_key]), Venda[Tipo de Operação] = "VENDA"), "@fat", [Faturamento]) VAR Topo = ROUNDUP(COUNTROWS(Clientes) / 5, 0) RETURN DIVIDE(SUMX(TOPN(Topo, Clientes, [@fat], DESC), [@fat]), [Faturamento])` | `dw.fato_venda` | 73,4% |
| Dias sem Comprar | Dias entre a última compra do cliente e a data de corte (31/12/2025). | `VAR k = CALCULATE(MAX(Venda[data_key]), Venda[Tipo de Operação] = "VENDA", REMOVEFILTERS('Calendário')) RETURN IF(ISBLANK(k), BLANK(), INT(DATE(2025, 12, 31) - DATE(INT(k / 10000), MOD(INT(k / 100), 100), MOD(k, 100))))` | `dw.fato_venda` |  |
| Clientes sem Compra há Mais de 90 Dias | Fotografia em 31/12/2025: clientes que já compraram e estão há mais de 90 dias sem comprar. Não muda com o filtro de ano. | `VAR Limite = DATE(2025, 12, 31) - 90 VAR Clientes = ADDCOLUMNS(VALUES(Cliente[cliente_key]), "@ultima", CALCULATE(MAX(Venda[data_key]), Venda[Tipo de Operação] = "VENDA", REMOVEFILTERS('Calendário'))) RETURN COUNTROWS(FILTER(Clientes, NOT ISBLANK([@ultima]) && [@ultima] < YEAR(Limite) * 10000 + MONTH(Limite) * 100 + DAY(Limite)))` | `dw.dim_cliente`, `dw.fato_venda` | 81 |
| Faturamento em 2024 e 2025 | Faturamento dos dois anos, ignorando o filtro de data. Base para comparar os clientes parados. | `CALCULATE([Faturamento], REMOVEFILTERS('Calendário'))` | `dw.fato_venda` |  |
| Faturamento dos Parados | Faturamento dos dois anos só dos clientes parados há mais de 90 dias: na tabela, os outros clientes ficam de fora. | `IF([Dias sem Comprar] > 90, [Faturamento em 2024 e 2025])` | `dw.fato_venda` |  |
| Dias Parado | Dias sem comprar, só para os clientes parados há mais de 90 dias (vazio para os demais). | `IF([Dias sem Comprar] > 90, [Dias sem Comprar])` | `dw.fato_venda` |  |

### 3. Comparativos

| Indicador | Definição | Fórmula DAX | Fonte | 2025 |
|---|---|---|---|---:|
| Faturamento Ano Anterior | Faturamento no mesmo período do ano anterior. | `CALCULATE([Faturamento], SAMEPERIODLASTYEAR('Calendário'[Data]))` | `dw.fato_venda` |  |
| Faturamento vs Ano Anterior % | Variação do faturamento contra o mesmo período do ano anterior. | `DIVIDE([Faturamento] - [Faturamento Ano Anterior], [Faturamento Ano Anterior])` | `dw.fato_venda` |  |
| Margem vs Ano Anterior (p.p.) | Diferença da margem comercial contra o mesmo período do ano anterior, em pontos percentuais. | `VAR Antes = CALCULATE([Margem Comercial %], SAMEPERIODLASTYEAR('Calendário'[Data])) RETURN IF(ISBLANK(Antes), BLANK(), ([Margem Comercial %] - Antes) * 100)` | `dw.fato_venda` |  |
| Ticket Médio vs Ano Anterior % | Variação do ticket médio contra o mesmo período do ano anterior. | `VAR Antes = CALCULATE([Ticket Médio], SAMEPERIODLASTYEAR('Calendário'[Data])) RETURN DIVIDE([Ticket Médio] - Antes, Antes)` | `dw.fato_venda` |  |
