# Dicionário de dados: modelo estrela (`dw`)

Data de corte: **31/12/2025**. Status de títulos, atrasos e faixas de aging são calculados nessa data.

## Dimensões

### dim_calendario
Um dia por linha, de 2023 a 2026.

| Coluna | Descrição |
|---|---|
| data_key | Chave no formato aaaammdd |
| ano, trimestre, mes, nome_mes, mes_abrev | Partes da data |
| ano_mes / mes_ano | 202401 (para ordenar) / jan/2024 (para exibir) |
| dia_semana / nome_dia_semana | 1 = segunda-feira |
| feriado / dia_util | Feriados nacionais e do RS; dia útil = segunda a sexta sem feriado |
| primeiro_dia_mes | Usado para ligar fatos mensais |

### dim_filial
Matriz Porto Alegre (1), Filial Caxias do Sul (2), Filial Pelotas (3). A chave é o próprio id da filial, que também é a série das notas fiscais.

### dim_centro_custo
CC01 Diretoria · CC02 Comercial · CC03 Logística · CC04 Financeiro · CC05 Recursos Humanos · CC06 Compras · CC07 Tecnologia da Informação · CC08 Administrativo.

### dim_conta
Plano de contas gerencial.

| Coluna | Descrição |
|---|---|
| cod_conta / descricao | Ex.: 5.09 Combustível |
| grupo_dre | Receita bruta, Deduções da receita, CMV, Despesas com pessoal, administrativas, logísticas, comerciais, Resultado financeiro |
| ordem_grupo | Ordem das linhas na DRE |
| sinal | +1 para receita, −1 para deduções, custos e despesas |
| entra_dre | 0 para a conta 1.05 (compra de mercadoria vai para o estoque, não para a DRE) |

### dim_produto
90 produtos em 6 categorias (Bebidas, Mercearia, Laticínios, Limpeza, Higiene, Congelados), com fornecedor principal e preço de tabela de jan/2024. A tabela teve reajustes de 3% em jul/2024 e 5,5% em jan/2025.

### dim_cliente
420 clientes B2B: tipo (Supermercado, Mercado de bairro, Restaurante, Padaria, Lanchonete, Hotel), cidade, filial que atende, data de cadastro, condição de pagamento, limite de crédito e situação.

### dim_fornecedor
Fornecedores de mercadoria (com prazo de pagamento e lead time prometido), prestadores de serviço e órgãos de governo (impostos e encargos).

### dim_funcionario
Todos os funcionários que passaram pela empresa no período.

| Coluna | Descrição |
|---|---|
| faixa_etaria | Idade no desligamento ou na data de corte; "Não informada" quando o RH não tem a data de nascimento |
| tipo_desligamento | Voluntário (pedido de demissão) ou Involuntário |
| tempo_casa_meses / faixa_tempo_casa | Até o desligamento ou a data de corte |
| ativo | 1 se não tem data de desligamento |

## Fatos

### fato_venda (item de nota fiscal)
Só notas faturadas. Notas canceladas ficam no staging e não entram. Devoluções têm `tipo_operacao = DEVOLUCAO` e quantidades e valores **negativos**.

| Coluna | Descrição |
|---|---|
| qtd_pedida / qtd_faturada | A diferença é ruptura de estoque (pedido não atendido) |
| valor_bruto | qtd_faturada × preço |
| valor_desconto / receita_liquida | Desconto comercial e receita após desconto |
| custo_total | qtd_faturada × custo médio do estoque no dia (base do CMV) |

### fato_conta_receber (título / parcela)
| Coluna | Descrição |
|---|---|
| status | PAGO, A VENCER ou VENCIDO na data de corte |
| dias_atraso | Pago: dias entre vencimento e pagamento. Vencido: dias até a data de corte |
| faixa_aging | Liquidado, A vencer, 1 a 30, 31 a 60, 61 a 90, Mais de 90 dias |
| juros_multa | Valor pago − valor original |

### fato_conta_pagar (título)
Mercadorias (conta 1.05), despesas operacionais, folha, encargos, benefícios e impostos. Tem competência (mês da DRE), emissão, vencimento e pagamento (caixa).

### fato_dre (mês × conta × centro de custo × filial)
DRE realizada por competência. Receita, devoluções e CMV vêm de `fato_venda`; as demais contas vêm do contas a pagar. `valor_resultado` já tem o sinal aplicado: a soma dá o resultado do período.

### fato_orcamento (mês × conta × centro de custo)
Orçamento anual aprovado pela controladoria, sem abertura por filial.

### fato_compra (item de pedido de compra)
Datas de pedido, entrega prevista e real. `entregue_no_prazo` e `dias_atraso_entrega` medem a pontualidade do fornecedor. Pedidos em aberto na data de corte não têm entrega real.

### fato_estoque_movimento (movimento)
Saldo inicial (01/01/2024), entradas por compra, saídas por venda e devoluções de clientes, todos a custo. A soma acumulada por produto dá a posição de estoque em qualquer data.

### fato_ponto (funcionário × mês)
Dias previstos e trabalhados, faltas, dias de atestado e horas extras.

### fato_quadro_mensal (funcionário × mês)
Uma linha por funcionário em cada mês em que esteve na empresa, com indicadores de ativo no início e no fim do mês, admissão, desligamento e desligamento voluntário. Base do headcount e da rotatividade:

> Rotatividade do mês = desligamentos ÷ média entre o headcount do início e o do fim do mês

## Views de apoio

| View | Pergunta |
|---|---|
| `vw_curva_abc_produto` | Quais produtos fazem 80% da receita? |
| `vw_orcado_realizado` | Onde o realizado fugiu do orçamento? |
| `vw_aging_receber` | Quem deve, quanto e há quanto tempo? |
| `vw_turnover_mensal` | Qual setor perde mais gente? |
| `vw_desempenho_fornecedor` | Quais fornecedores atrasam? |
| `vw_estoque_fim_mes` | Qual a posição de estoque no fim de cada mês? |
