# Relatório de qualidade dos dados

Gerado automaticamente por `python/etl.py` a cada execução.

## Cadastro de produtos (Excel de compras)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Categoria escrita de formas diferentes (ex.: BEBIDAS, bebida, Laticinios) | 9 | Padronizada para as 6 categorias oficiais |
| Categoria não reconhecida | 0 | Revisar manualmente |

## Fornecedores (ERP)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| CNPJ com máscara (pontos, barra e traço) | 24 | Mantidos só os 14 dígitos |
| CNPJ com dígito verificador inválido | 0 | Nenhuma ação (todos válidos) |

## Clientes (ERP)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Razão social com espaços sobrando | 30 | Espaços removidos |
| Razão social toda em maiúsculas | 40 | Convertida para nome próprio |
| Cidade com grafia diferente (ex.: POA, Porto alegre, Sao Leopoldo) | 47 | Padronizada pela grafia mais usada de cada cidade |
| CNPJ com máscara | 219 | Mantidos só os 14 dígitos |
| CNPJ com dígito verificador inválido | 0 | Nenhuma ação (todos válidos) |
| Cliente cadastrado duas vezes (mesmo CNPJ, códigos diferentes) | 4 | Unificado no código mais antigo; tabela de-para aplicada em vendas e contas a receber |

## Vendas - itens de nota fiscal (ERP)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Linha exportada em duplicidade (idêntica a outra) | 286 | Removida |
| Código de produto com espaço ou minúscula (ex.: ' p0012') | 387 | Padronizado |
| Produto inexistente no cadastro | 0 | Nenhum após a padronização |
| Venda lançada no código duplicado do cliente | 1.749 | Apontada para o código mestre |
| Preço unitário 100 vezes maior que o normal (vírgula esquecida na digitação) | 6 | Dividido por 100 |
| Item repetido na mesma nota (série + nota + produto) | 0 | Nenhum após remover as duplicidades |
| Notas canceladas | 364 | Mantidas com status; o modelo filtra na carga |

## Pedidos de compra (ERP)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Pedido ainda não entregue na data de corte | 11 | Mantido sem data de entrega real |

## Contas a receber (financeiro)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Pagamento com data anterior à emissão (ano digitado errado na baixa) | 12 | Ano corrigido (+1) quando a nova data fica entre a emissão e a data de corte |
| Pagamento anterior à emissão sem correção possível | 0 | Data apagada para revisão do financeiro |
| Título no código duplicado do cliente | 340 | Apontado para o código mestre |

## Contas a pagar (planilha do financeiro)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Datas em formato aaaa-mm-dd misturadas com dd/mm/aaaa | 1.550 | Lidas nos dois formatos |
| Valores como texto 'R$ 1.234,56' | 3.598 | Convertidos para número |
| Fornecedor sem cadastro (CNPJ não encontrado) | 0 | Nenhum: todos ligados ao cadastro pelo CNPJ |
| Centro de custo em branco | 103 | 24 preenchidos pelo setor citado na descrição e 79 pelo centro de custo mais usado na mesma conta |

## Orçamento (Excel da controladoria)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Orçamento 2024: linhas cujo total não bate com a soma dos meses | 0 | Conferido; a coluna Total é descartada |
| Orçamento 2025: linhas cujo total não bate com a soma dos meses | 0 | Conferido; a coluna Total é descartada |
| Formato largo (um mês por coluna) com 3 linhas de título | 2 | Títulos ignorados e meses transformados em linhas |

## Quadro de funcionários (Excel do RH)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Salário como texto 'R$ 2.350,00' | 171 | Convertido para número |
| Setor escrito de formas diferentes (ex.: Logistica, Adm, Vendas) | 31 | Ligado ao código do centro de custo |
| Setor não reconhecido | 0 | Revisar manualmente |
| Data de nascimento em branco | 9 | Mantida em branco (não dá para inventar); a faixa etária fica 'Não informada' |

## Ponto mensal (um CSV por mês do RH)

| Verificação | Ocorrências | O que foi feito |
|---|---:|---|
| Arquivos mensais para consolidar | 24 | Empilhados em uma tabela só |
| Arquivos com o layout novo (colunas renomeadas e em outra ordem a partir de mar/2025) | 10 | Colunas mapeadas para o layout padrão |
| Horas extras em texto hh:mm | 2.244 | Convertidas para horas decimais (ex.: 12:30 = 12,5) |

## Arquivos gerados em `data/tratado/`

| Arquivo | Linhas |
|---|---:|
| `filial.csv` | 3 |
| `centro_custo.csv` | 8 |
| `conta.csv` | 17 |
| `produto.csv` | 90 |
| `fornecedor.csv` | 40 |
| `cliente.csv` | 420 |
| `de_para_cliente.csv` | 4 |
| `venda_item.csv` | 95.415 |
| `pedido_compra_item.csv` | 2.008 |
| `estoque_inicial.csv` | 90 |
| `conta_receber.csv` | 25.588 |
| `conta_pagar.csv` | 3.598 |
| `orcamento.csv` | 936 |
| `funcionario.csv` | 171 |
| `ponto_mensal.csv` | 2.244 |
