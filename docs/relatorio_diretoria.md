# Três decisões para 2026: relatório para a diretoria

Distribuidora Sul Ltda. (dados fictícios) · janeiro de 2026 · dados de 2024 e 2025

Leitura dos quatro painéis (Financeiro, People Analytics, Compras e Estoque, Comercial) em forma de decisão. O ganho de cada decisão é calculado em SQL, sobre o mesmo banco dos painéis, na view [`dw.vw_relatorio_diretoria`](../sql/11_relatorio_diretoria.sql). A [versão para leitura](https://lucasgama.vercel.app/relatorio.html) está no portfólio.

## Resumo

2025 fechou com faturamento 6,6% maior, mas com resultado R$ 1,9 mi abaixo do orçado. Os painéis apontam três decisões que, num cenário conservador, somam **R$ 441 mil por ano**, cerca de **20% do resultado líquido de 2025** (R$ 2,23 mi).

| # | Decisão | Responsável | Ganho estimado por ano | Primeiro passo |
|---|---|---|---:|---|
| 1 | Recuperar os 32 clientes que pararam de comprar em 2025 | Comercial | R$ 333 mil de lucro bruto | Ligar para os 8 supermercados em 30 dias |
| 2 | Exigir pontualidade dos 9 fornecedores que mais atrasam | Compras | R$ 55 mil de lucro bruto | Acordo de prazo, começando pela Gaúcha Alimentos |
| 3 | Reduzir as saídas no primeiro ano de ajudantes de entrega e vendedores | RH e Logística | R$ 53 mil de custo de reposição | Integração nos primeiros 90 dias |

## 1. Recuperar os clientes que pararam de comprar

**O que os dados mostram**
- 32 clientes compraram em 2025 e estão há mais de 90 dias sem comprar. Em 2024 eles faturaram **R$ 5,0 mi**; em 2025, R$ 2,85 mi até pararem.
- 8 deles são supermercados e respondem por R$ 3,8 mi (76%) do que esses clientes compravam.
- Juntos, davam **R$ 1,0 mi de lucro bruto por ano**. A carteira já vinha encolhendo: 386 clientes compraram em 2024 e 371 em 2025 (painel Comercial).

**O que propomos**
- Entregar a lista aos vendedores por ordem de faturamento e ligar para os 8 supermercados nos próximos 30 dias.
- Registrar o motivo de cada parada (preço, prazo de entrega, falta de produto, troca de vendedor).
- Acompanhar todo mês, no painel Comercial, os clientes ativos que passam de 60 dias sem comprar, antes que virem perda.

**Ganho estimado:** R$ 333 mil de lucro bruto por ano se 1 em cada 3 voltar a comprar como em 2024.

## 2. Exigir pontualidade dos fornecedores que mais atrasam

**O que os dados mostram**
- 9 fornecedores entregaram menos de 70% dos pedidos de 2025 no prazo.
- Nos produtos deles, faltou estoque em **2,2% da demanda**, mais que o dobro dos demais fornecedores (1,0%). Foram R$ 514 mil em vendas perdidas.
- A Gaúcha Alimentos tem a maior venda perdida entre todos os fornecedores (R$ 156 mil) e entregou só 58% dos pedidos no prazo.

**O que propomos**
- Acordo de nível de serviço com os 9, com prazo de entrega e desconto por atraso, começando pela Gaúcha Alimentos.
- Estoque de segurança maior nos itens classe A desses fornecedores enquanto a pontualidade não melhora, financiado pela redução do estoque dos itens que não faltam (ver "Também no radar").
- Um segundo fornecedor para os itens classe A mais afetados.

**Ganho estimado:** R$ 272 mil por ano em vendas que hoje faltam e R$ 55 mil de lucro bruto, se a ruptura desses fornecedores cair ao nível dos pontuais. O ganho não medido é o cliente que deixa de procurar o produto no concorrente.

## 3. Reduzir as saídas no primeiro ano

**O que os dados mostram**
- 50 das 80 saídas de 2024 e 2025 (62,5%) aconteceram antes de um ano de casa. Metade delas (25) foi de ajudantes de entrega e vendedores.
- As saídas de vendedores externos passaram de **5 em 2024 para 13 em 2025**. Cada saída passa a carteira para um vendedor novo: 153 clientes trocaram de vendedor nos dois anos (painel Comercial).
- Em 2025, quem saiu faltava 30% mais do que quem ficou (0,52 contra 0,40 falta por mês trabalhado, painel People Analytics): as faltas são um sinal de alerta.

**O que propomos**
- Integração estruturada nos primeiros 90 dias para ajudantes e vendedores, com um responsável por novato.
- Usar as faltas dos primeiros meses como alerta para uma conversa com o gestor.
- Entrevista de desligamento padronizada, para saber por que os vendedores estão saindo.

**Ganho estimado:** R$ 53 mil por ano em custo de reposição com metade das saídas no primeiro ano. O ganho maior, menos visível, é manter o cliente com o mesmo vendedor.

## Também no radar

- **Frota acima do orçado pelo segundo ano:** R$ 113 mil em 2025 (combustível +18,6%, manutenção +31,3%) e R$ 79 mil em 2024. O orçamento de 2026 deveria partir do custo por entrega, com o consumo acompanhado por veículo.
- **Inadimplência do pequeno varejo:** 25% do que mercados de bairro, padarias e lanchonetes têm em aberto está vencido, contra 7,9% nos supermercados. R$ 259 mil estão vencidos há mais de 90 dias. Vale um limite de crédito menor para novos clientes desses tipos.
- **Estoque maior e girando menos:** R$ 3,19 mi em dez/2025, 16% acima de dez/2024 (R$ 2,74 mi), com o giro caindo de 17,7 para 15,8 vezes. É desse capital parado que sai o estoque de segurança da decisão 2.

## Premissas

- **Lucro bruto** = faturamento − impostos sobre vendas (14,1% da receita bruta em 2025) − custo das mercadorias, como na DRE.
- **Decisão 1:** o faturamento de 2024 desses clientes (um ano inteiro de compras) é a base do que está em jogo por ano.
- **Decisão 2:** fornecedor impontual é o que entregou menos de 70% dos pedidos de 2025 no prazo; a venda perdida é atribuída ao fornecedor principal do produto.
- **Decisão 3:** cada substituição custa uma folha mensal completa do cargo (salário × 1,49, com encargos e benefícios, na proporção da DRE de 2025), cobrindo rescisão, seleção e treinamento. É uma estimativa conservadora, a validar com o RH.

## Números do relatório

Calculados por `SELECT * FROM dw.vw_relatorio_diretoria ORDER BY ordem` (data de corte 31/12/2025).

| Decisão | Indicador | Valor |
|---|---|---:|
| 1 | Clientes que compraram em 2025 e estão parados há mais de 90 dias | 32 |
| 1 | Faturamento desses clientes em 2024 | R$ 5.002.407 |
| 1 | Faturamento desses clientes em 2025, até pararem | R$ 2.849.954 |
| 1 | Supermercados entre eles / faturamento deles em 2024 | 8 / R$ 3.798.734 |
| 1 | Lucro bruto desses clientes por ano (base 2024) | R$ 1.000.314 |
| 1 | Lucro bruto recuperado com 1 em cada 3 clientes | R$ 333.438 |
| 2 | Fornecedores com menos de 70% dos pedidos no prazo | 9 |
| 2 | Ruptura nos produtos desses fornecedores / dos demais | 2,15% / 1,01% |
| 2 | Venda perdida nos produtos desses fornecedores | R$ 513.840 |
| 2 | Venda perdida a mais que a dos fornecedores pontuais | R$ 271.950 |
| 2 | Lucro bruto dessa venda perdida a mais | R$ 54.773 |
| 2 | Maior venda perdida de um só fornecedor / pedidos no prazo | R$ 155.851 / 57,5% |
| 3 | Saídas antes de 1 ano de casa em 2024 e 2025 / ajudantes e vendedores | 50 / 25 |
| 3 | Saídas de vendedores externos em 2024 / 2025 | 5 / 13 |
| 3 | Custo da folha por real de salário | 1,49 |
| 3 | Custo estimado de repor as saídas de 2025 / com metade delas | R$ 105.357 / R$ 52.678 |
| Radar | Frota acima do orçado em 2025 / 2024 | R$ 112.745 / R$ 79.032 |
| Radar | Combustível / manutenção acima do orçado em 2025 | 18,6% / 31,3% |
| Radar | Títulos vencidos há mais de 90 dias | R$ 258.573 |
| Radar | Carteira vencida do pequeno varejo / dos supermercados | 25,2% / 7,9% |
| Radar | Estoque em dez/2024 / dez/2025 | R$ 2.744.913 / R$ 3.188.982 |
| Radar | Giro de estoque 2024 / 2025 | 17,7 / 15,8 |
| Resumo | Ganho somado das três decisões por ano | R$ 440.890 |
| Resumo | Resultado líquido de 2025 / ganho em % dele | R$ 2.234.353 / 19,7% |
