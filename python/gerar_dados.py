"""
Gera os dados brutos da Distribuidora Sul Ltda., uma empresa fictícia.

Simula dois anos de operação (2024 e 2025) de uma distribuidora de alimentos,
bebidas, limpeza e higiene com matriz e centro de distribuição em Porto Alegre
e filiais comerciais em Caxias do Sul e Pelotas. Os arquivos são gravados do
jeito que sairiam dos "sistemas de origem": exportações do ERP em CSV e
planilhas do RH e da controladoria em Excel.

Os dados têm comportamento de negócio de propósito (sazonalidade, clientes que
atrasam, fornecedores impontuais, rotatividade maior em cargos operacionais) e
recebem, no fim, problemas de qualidade comuns em sistemas reais, que o ETL
detecta e corrige (ver docs/relatorio_qualidade.md).

Uso:   python python/gerar_dados.py
Saída: data/bruto/
"""
from __future__ import annotations

import calendar
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 2024
INICIO = date(2024, 1, 1)
FIM = date(2025, 12, 31)
RAIZ = Path(__file__).resolve().parents[1]
BRUTO = RAIZ / "data" / "bruto"

rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Calendário
# ---------------------------------------------------------------------------
FERIADOS = {
    date(2024, 1, 1), date(2024, 2, 12), date(2024, 2, 13), date(2024, 3, 29),
    date(2024, 4, 21), date(2024, 5, 1), date(2024, 5, 30), date(2024, 9, 7),
    date(2024, 9, 20), date(2024, 10, 12), date(2024, 11, 2), date(2024, 11, 15),
    date(2024, 11, 20), date(2024, 12, 25),
    date(2025, 1, 1), date(2025, 3, 3), date(2025, 3, 4), date(2025, 4, 18),
    date(2025, 4, 21), date(2025, 5, 1), date(2025, 6, 19), date(2025, 9, 7),
    date(2025, 9, 20), date(2025, 10, 12), date(2025, 11, 2), date(2025, 11, 15),
    date(2025, 11, 20), date(2025, 12, 25),
}


def datas(inicio: date, fim: date):
    d = inicio
    while d <= fim:
        yield d
        d += timedelta(days=1)


def meses():
    a, m = INICIO.year, INICIO.month
    while (a, m) <= (FIM.year, FIM.month):
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def fim_do_mes(a: int, m: int) -> date:
    return date(a, m, calendar.monthrange(a, m)[1])


def mes_seguinte(a: int, m: int) -> tuple[int, int]:
    return (a + 1, 1) if m == 12 else (a, m + 1)


def dia_de_venda(d: date) -> bool:
    """A distribuidora fatura de segunda a sábado."""
    return d.weekday() < 6 and d not in FERIADOS


def dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in FERIADOS


def proximo_dia_util(d: date) -> date:
    while not dia_util(d):
        d += timedelta(days=1)
    return d


def data_aleatoria(inicio: date, fim: date, r=rng) -> date:
    return inicio + timedelta(days=r.randint(0, max(0, (fim - inicio).days)))


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def poisson(lam: float, r=rng) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, round(r.gauss(lam, math.sqrt(lam))))
    limite, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= limite:
            return k
        k += 1


def gerar_cnpj() -> str:
    """CNPJ fictício com dígitos verificadores válidos."""
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        resto = sum(d * p for d, p in zip(base, pesos)) % 11
        base.append(0 if resto < 2 else 11 - resto)
    return "".join(map(str, base))


def mascarar_cnpj(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def dec(v: float, casas: int = 2) -> str:
    """Número no formato do ERP: vírgula decimal, sem separador de milhar."""
    return f"{v:.{casas}f}".replace(".", ",")


def reais(v: float) -> str:
    """Número no formato de planilha: R$ 1.234,56."""
    return "R$ " + f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def br_data(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def fator_preco(d: date) -> float:
    """Reajustes da tabela de preços (e dos custos de compra)."""
    if d >= date(2025, 1, 1):
        return 1.03 * 1.055
    if d >= date(2024, 7, 1):
        return 1.03
    return 1.0


# ---------------------------------------------------------------------------
# Cadastros básicos
# ---------------------------------------------------------------------------
FILIAIS = [
    dict(id=1, nome="Matriz Porto Alegre", cidade="Porto Alegre", peso=0.50,
         cidades=["Porto Alegre", "Canoas", "Gravataí", "Novo Hamburgo", "São Leopoldo", "Viamão", "Cachoeirinha"]),
    dict(id=2, nome="Filial Caxias do Sul", cidade="Caxias do Sul", peso=0.30,
         cidades=["Caxias do Sul", "Bento Gonçalves", "Farroupilha", "Garibaldi", "Flores da Cunha"]),
    dict(id=3, nome="Filial Pelotas", cidade="Pelotas", peso=0.20,
         cidades=["Pelotas", "Rio Grande", "Canguçu", "Capão do Leão"]),
]
FILIAL = {f["id"]: f for f in FILIAIS}

CENTROS_CUSTO = [
    ("CC01", "Diretoria"), ("CC02", "Comercial"), ("CC03", "Logística"), ("CC04", "Financeiro"),
    ("CC05", "Recursos Humanos"), ("CC06", "Compras"), ("CC07", "Tecnologia da Informação"),
    ("CC08", "Administrativo"),
]
NOME_CC = dict(CENTROS_CUSTO)

PLANO_CONTAS = [
    ("1.05", "Estoque de mercadorias", "Balanço (não entra na DRE)"),
    ("3.01", "Receita bruta de vendas", "Receita bruta"),
    ("3.02", "Devoluções de vendas", "Deduções da receita"),
    ("3.03", "Impostos sobre vendas", "Deduções da receita"),
    ("4.01", "Custo das mercadorias vendidas", "CMV"),
    ("5.01", "Salários e ordenados", "Despesas com pessoal"),
    ("5.02", "Encargos sociais", "Despesas com pessoal"),
    ("5.03", "Benefícios", "Despesas com pessoal"),
    ("5.04", "Aluguel", "Despesas administrativas"),
    ("5.05", "Energia elétrica e água", "Despesas administrativas"),
    ("5.06", "Material de escritório", "Despesas administrativas"),
    ("5.07", "Serviços de terceiros", "Despesas administrativas"),
    ("5.08", "Tecnologia e software", "Despesas administrativas"),
    ("5.09", "Combustível", "Despesas logísticas"),
    ("5.10", "Manutenção de frota", "Despesas logísticas"),
    ("5.11", "Marketing e trade", "Despesas comerciais"),
    ("6.01", "Tarifas bancárias e juros", "Resultado financeiro"),
]

NOMES_M = ["João", "Pedro", "Lucas", "Gabriel", "Rafael", "Matheus", "Felipe", "Bruno", "Gustavo",
           "Leonardo", "Rodrigo", "Eduardo", "Diego", "Marcelo", "André", "Thiago", "Vinícius",
           "Carlos", "Fernando", "Ricardo", "Daniel", "Alexandre", "Leandro", "Fábio", "Paulo",
           "Júlio", "César", "Maurício", "Henrique", "Otávio"]
NOMES_F = ["Ana", "Maria", "Juliana", "Camila", "Fernanda", "Patrícia", "Aline", "Bruna", "Letícia",
           "Larissa", "Gabriela", "Mariana", "Carolina", "Tatiane", "Vanessa", "Daniela", "Renata",
           "Luana", "Priscila", "Débora", "Natália", "Bianca", "Jéssica", "Sabrina", "Cláudia",
           "Simone", "Luciana", "Raquel", "Beatriz", "Isadora"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Pereira", "Lima", "Ferreira", "Costa",
              "Rodrigues", "Almeida", "Nunes", "Machado", "Rocha", "Becker", "Schmidt", "Müller",
              "Weber", "Fontana", "Rossi", "Bortolini", "Zanella", "Dalla Costa", "Pinto", "Mendes",
              "Barbosa", "Ribeiro", "Carvalho", "Teixeira", "Moraes", "Fagundes", "Brum", "Kunz",
              "Hoffmann", "Bertoldi", "Tonin"]

# ---------------------------------------------------------------------------
# Produtos e fornecedores
# ---------------------------------------------------------------------------
CATEGORIAS = {
    "Bebidas": [
        ("Refrigerante cola 2L - fardo 6un", "FD", 38.90), ("Refrigerante guaraná 2L - fardo 6un", "FD", 33.50),
        ("Refrigerante laranja 2L - fardo 6un", "FD", 31.20), ("Refrigerante cola lata 350ml - fardo 12un", "FD", 30.40),
        ("Água mineral 500ml - fardo 12un", "FD", 14.10), ("Água mineral com gás 500ml - fardo 12un", "FD", 16.80),
        ("Cerveja pilsen lata 350ml - fardo 12un", "FD", 42.60), ("Cerveja puro malte lata 350ml - fardo 12un", "FD", 52.30),
        ("Cerveja long neck 330ml - caixa 24un", "CX", 98.00), ("Cerveja sem álcool lata 350ml - fardo 12un", "FD", 47.90),
        ("Suco de uva integral 1L - caixa 6un", "CX", 54.00), ("Suco néctar pêssego 1L - caixa 12un", "CX", 59.80),
        ("Energético 250ml - fardo 6un", "FD", 36.00), ("Chá gelado limão 1,5L - fardo 6un", "FD", 29.70),
        ("Isotônico 500ml - fardo 6un", "FD", 24.30), ("Vinho tinto suave 750ml - caixa 6un", "CX", 72.00),
        ("Espumante moscatel 750ml - caixa 6un", "CX", 119.00), ("Água tônica 350ml - fardo 6un", "FD", 19.90),
        ("Água de coco 1L - caixa 12un", "CX", 66.00), ("Suco em pó laranja - caixa 15un", "CX", 9.40),
    ],
    "Mercearia": [
        ("Arroz branco tipo 1 5kg - fardo 6un", "FD", 119.00), ("Feijão preto 1kg - fardo 10un", "FD", 69.90),
        ("Feijão carioca 1kg - fardo 10un", "FD", 72.40), ("Açúcar refinado 1kg - fardo 10un", "FD", 41.50),
        ("Café torrado e moído 500g - caixa 10un", "CX", 154.00), ("Óleo de soja 900ml - caixa 20un", "CX", 129.00),
        ("Macarrão espaguete 500g - fardo 20un", "FD", 59.60), ("Macarrão parafuso 500g - fardo 20un", "FD", 60.20),
        ("Farinha de trigo 1kg - fardo 10un", "FD", 44.80), ("Sal refinado 1kg - fardo 10un", "FD", 15.20),
        ("Molho de tomate 340g - caixa 24un", "CX", 40.10), ("Extrato de tomate 190g - caixa 24un", "CX", 47.50),
        ("Biscoito recheado 140g - caixa 48un", "CX", 84.70), ("Biscoito cream cracker 400g - caixa 20un", "CX", 89.90),
        ("Erva-mate chimarrão 1kg - fardo 10un", "FD", 149.00), ("Achocolatado em pó 400g - caixa 24un", "CX", 164.00),
        ("Milho verde lata 200g - caixa 24un", "CX", 49.80), ("Atum ralado lata 170g - caixa 24un", "CX", 159.00),
        ("Maionese 500g - caixa 12un", "CX", 77.60), ("Azeite extra virgem 500ml - caixa 12un", "CX", 289.00),
    ],
    "Laticínios": [
        ("Leite UHT integral 1L - caixa 12un", "CX", 53.90), ("Leite UHT desnatado 1L - caixa 12un", "CX", 55.80),
        ("Queijo mussarela fatiado 150g - caixa 20un", "CX", 129.00), ("Queijo prato fatiado 150g - caixa 20un", "CX", 139.00),
        ("Manteiga com sal 200g - caixa 24un", "CX", 209.00), ("Iogurte natural 170g - caixa 24un", "CX", 54.70),
        ("Iogurte grego 100g - caixa 24un", "CX", 69.90), ("Requeijão cremoso 200g - caixa 24un", "CX", 149.00),
        ("Creme de leite 200g - caixa 27un", "CX", 74.50), ("Leite condensado 395g - caixa 27un", "CX", 159.00),
        ("Bebida láctea morango 900ml - caixa 12un", "CX", 59.40), ("Margarina 500g - caixa 12un", "CX", 69.80),
        ("Doce de leite 400g - caixa 12un", "CX", 84.60), ("Nata 300g - caixa 12un", "CX", 89.90),
        ("Queijo colonial peça - kg", "KG", 38.50),
    ],
    "Limpeza": [
        ("Detergente líquido 500ml - caixa 24un", "CX", 39.80), ("Sabão em pó 1,6kg - fardo 8un", "FD", 129.00),
        ("Amaciante 2L - caixa 6un", "CX", 59.70), ("Água sanitária 2L - caixa 6un", "CX", 23.90),
        ("Desinfetante 2L - caixa 6un", "CX", 35.80), ("Esponja dupla face - pacote 60un", "PCT", 44.90),
        ("Saco de lixo 100L - fardo 10 pacotes", "FD", 64.50), ("Limpador multiuso 500ml - caixa 12un", "CX", 37.60),
        ("Papel toalha - fardo 12 rolos", "FD", 47.80), ("Álcool 70% 1L - caixa 12un", "CX", 69.90),
        ("Lustra móveis 200ml - caixa 12un", "CX", 54.80), ("Sabão em barra - fardo 20 pacotes", "FD", 94.70),
    ],
    "Higiene": [
        ("Papel higiênico folha dupla 12 rolos - fardo 4 pacotes", "FD", 74.90), ("Sabonete 85g - caixa 72un", "CX", 99.80),
        ("Creme dental 90g - caixa 24un", "CX", 69.60), ("Shampoo 350ml - caixa 12un", "CX", 109.00),
        ("Condicionador 350ml - caixa 12un", "CX", 114.00), ("Desodorante aerossol 150ml - caixa 12un", "CX", 149.00),
        ("Fralda descartável G - fardo 4 pacotes", "FD", 199.00), ("Absorvente - caixa 24 pacotes", "CX", 84.90),
        ("Escova dental - caixa 12un", "CX", 34.80), ("Fio dental - caixa 12un", "CX", 39.70),
        ("Sabonete líquido refil 1L - caixa 6un", "CX", 79.90),
    ],
    "Congelados": [
        ("Pão de queijo 1kg - caixa 10un", "CX", 179.00), ("Batata pré-frita 2kg - caixa 6un", "CX", 114.00),
        ("Lasanha bolonhesa 600g - caixa 12un", "CX", 149.00), ("Pizza mussarela 460g - caixa 10un", "CX", 119.00),
        ("Hambúrguer bovino 672g - caixa 12un", "CX", 189.00), ("Nuggets de frango 300g - caixa 20un", "CX", 139.00),
        ("Sorvete 2L - caixa 6un", "CX", 94.80), ("Polpa de fruta 1kg - caixa 10un", "CX", 84.50),
        ("Peito de frango congelado 1kg - caixa 10un", "CX", 169.00), ("Linguiça toscana 1kg - caixa 10un", "CX", 159.00),
        ("Coxa e sobrecoxa 1kg - caixa 10un", "CX", 109.00), ("Picolé sortido - caixa 30un", "CX", 59.90),
    ],
}

# Multiplicador da demanda por mês (índice 0 = janeiro)
SAZONALIDADE_CATEGORIA = {
    "Bebidas":    [1.35, 1.30, 1.15, 0.95, 0.85, 0.80, 0.80, 0.85, 0.95, 1.05, 1.15, 1.40],
    "Congelados": [1.25, 1.20, 1.10, 0.95, 0.90, 0.85, 0.85, 0.90, 0.95, 1.00, 1.10, 1.30],
    "Laticínios": [0.95, 0.95, 1.00, 1.05, 1.08, 1.10, 1.10, 1.05, 1.00, 0.95, 0.95, 1.00],
    "Mercearia":  [0.95, 0.95, 1.00, 1.00, 1.00, 1.05, 1.05, 1.00, 1.00, 1.00, 1.05, 1.15],
    "Limpeza":    [1.00] * 12,
    "Higiene":    [1.00] * 11 + [1.10],
}
SAZONALIDADE_GERAL = [0.90, 0.90, 1.00, 0.98, 1.00, 0.98, 0.98, 1.00, 1.00, 1.03, 1.08, 1.22]

PREFIXOS_FORNECEDOR = ["Sul", "Pampa", "Gaúcha", "Serra", "Litoral", "Planalto", "Guaíba", "Missões",
                       "Fronteira", "Vale do Taquari", "Campos", "Coxilha"]
SUFIXOS_FORNECEDOR = ["Ltda", "S.A.", "Distribuidora Ltda", "Indústria e Comércio Ltda", "Atacado Ltda"]
RAMO = {"Bebidas": "Bebidas", "Mercearia": "Alimentos", "Laticínios": "Laticínios",
        "Limpeza": "Produtos de Limpeza", "Higiene": "Higiene e Cosméticos", "Congelados": "Frios e Congelados"}
CIDADES_FORNECEDOR = ["Porto Alegre", "Caxias do Sul", "Lajeado", "Estrela", "Santa Cruz do Sul", "Passo Fundo",
                      "Joinville", "Curitiba", "São Paulo", "Chapecó", "Teutônia", "Carlos Barbosa"]

FORNECEDORES_SERVICO = {
    "aluguel": ("Imobiliária Guaíba Administração de Bens Ltda", "Serviços", "Porto Alegre"),
    "energia": ("Energia Sul Distribuidora S.A.", "Serviços", "Porto Alegre"),
    "escritorio": ("Papelaria e Informática Central Ltda", "Serviços", "Porto Alegre"),
    "contabilidade": ("Farroupilha Assessoria Contábil Ltda", "Serviços", "Porto Alegre"),
    "juridico": ("Bertoldi & Zanella Advogados Associados", "Serviços", "Porto Alegre"),
    "facilities": ("Vigilância e Facilities Pampa Ltda", "Serviços", "Canoas"),
    "erp": ("TecnoSul Sistemas de Gestão Ltda", "Serviços", "Novo Hamburgo"),
    "internet": ("ConectaRS Telecomunicações Ltda", "Serviços", "Porto Alegre"),
    "combustivel": ("Rede de Postos Rota Sul Ltda", "Serviços", "Porto Alegre"),
    "manutencao": ("Auto Center Pampa Peças e Serviços Ltda", "Serviços", "Canoas"),
    "marketing": ("Agência Chimarrão Comunicação Ltda", "Serviços", "Porto Alegre"),
    "banco": ("Banco Horizonte Sul S.A.", "Serviços", "Porto Alegre"),
    "beneficios": ("Cartão Benefício Sul Ltda", "Serviços", "Porto Alegre"),
    "icms": ("Secretaria da Fazenda do RS - ICMS", "Governo", "Porto Alegre"),
    "federal": ("Receita Federal - PIS/COFINS", "Governo", "Brasília"),
    "encargos": ("INSS e FGTS - guias de recolhimento", "Governo", "Brasília"),
    "folha": ("Folha de pagamento - funcionários", "Folha", "Porto Alegre"),
}


def gerar_fornecedores_e_produtos():
    fornecedores, produtos, usados = [], [], set()
    for cat, itens in CATEGORIAS.items():
        grupo = []
        for _ in range(rng.randint(3, 5)):
            while True:
                nome = f"{rng.choice(PREFIXOS_FORNECEDOR)} {RAMO[cat]} {rng.choice(SUFIXOS_FORNECEDOR)}"
                if nome not in usados:
                    break
            usados.add(nome)
            f = dict(cod=f"F{len(fornecedores) + 1:03d}", razao_social=nome, cnpj=gerar_cnpj(),
                     tipo="Mercadorias", cidade=rng.choice(CIDADES_FORNECEDOR), categoria=cat,
                     prazo=rng.choice([21, 28, 28, 35]), lead=rng.randint(3, 9),
                     pontualidade=rng.choice([0.97, 0.95, 0.90, 0.85, 0.70]),
                     fator_custo=rng.uniform(0.97, 1.04))
            grupo.append(f)
            fornecedores.append(f)
        for desc, unid, custo in itens:
            produtos.append(dict(descricao=desc, categoria=cat, unidade=unid, custo=custo,
                                 preco=round(custo * rng.uniform(1.50, 1.72), 2),
                                 fornecedor=rng.choice(grupo)))
    for i, p in enumerate(produtos, start=1):
        p["cod"] = f"P{i:04d}"
    # Popularidade com cauda longa: poucos produtos concentram boa parte da venda (curva ABC)
    ordem = list(range(len(produtos)))
    rng.shuffle(ordem)
    for rank, i in enumerate(ordem, start=1):
        produtos[i]["popularidade"] = 1 / rank ** 1.25

    servico = {}
    for chave, (nome, tipo, cidade) in FORNECEDORES_SERVICO.items():
        f = dict(cod=f"F{len(fornecedores) + 1:03d}", razao_social=nome, cnpj=gerar_cnpj(), tipo=tipo,
                 cidade=cidade, categoria="", prazo=0, lead=0, pontualidade=1.0, fator_custo=1.0)
        fornecedores.append(f)
        servico[chave] = f
    return fornecedores, produtos, servico


# ---------------------------------------------------------------------------
# RH: quadro de funcionários, rotatividade, ponto e folha
# ---------------------------------------------------------------------------
CARGOS = [
    # cargo, centro de custo, vagas por filial, faixa salarial (jan/2024), risco mensal de saída,
    # horas extras típicas por mês, faixa de idade
    ("Diretor geral", "CC01", {1: 1}, (28000, 32000), 0.001, 0, (42, 60)),
    ("Diretor comercial", "CC01", {1: 1}, (22000, 26000), 0.002, 0, (38, 58)),
    ("Diretor financeiro", "CC01", {1: 1}, (22000, 26000), 0.002, 0, (38, 58)),
    ("Gerente comercial", "CC02", {1: 1}, (11000, 14000), 0.004, 0, (32, 55)),
    ("Supervisor de vendas", "CC02", {1: 1, 2: 1, 3: 1}, (6000, 7500), 0.008, 2, (28, 50)),
    ("Vendedor externo", "CC02", {1: 8, 2: 5, 3: 4}, (2800, 4200), 0.020, 4, (21, 45)),
    ("Gerente de logística", "CC03", {1: 1}, (10000, 12500), 0.004, 4, (32, 55)),
    ("Supervisor de logística", "CC03", {1: 1, 2: 1}, (5000, 6200), 0.008, 10, (28, 50)),
    ("Conferente", "CC03", {1: 6}, (2300, 2900), 0.020, 14, (20, 45)),
    ("Estoquista", "CC03", {1: 5}, (2100, 2600), 0.026, 16, (19, 40)),
    ("Motorista entregador", "CC03", {1: 9, 2: 5, 3: 4}, (2900, 3600), 0.012, 18, (24, 55)),
    ("Ajudante de entrega", "CC03", {1: 8, 2: 4, 3: 3}, (1700, 2000), 0.030, 14, (18, 35)),
    ("Gerente financeiro", "CC04", {1: 1}, (10500, 13000), 0.004, 2, (32, 55)),
    ("Analista financeiro", "CC04", {1: 2}, (4500, 6000), 0.010, 6, (23, 40)),
    ("Assistente financeiro", "CC04", {1: 2}, (2400, 3000), 0.015, 4, (20, 35)),
    ("Analista de RH", "CC05", {1: 2}, (4200, 5500), 0.010, 2, (23, 40)),
    ("Assistente de departamento pessoal", "CC05", {1: 1}, (2400, 3000), 0.014, 3, (20, 35)),
    ("Gerente de compras", "CC06", {1: 1}, (10000, 12500), 0.004, 2, (32, 55)),
    ("Comprador", "CC06", {1: 3}, (4000, 5500), 0.010, 4, (24, 45)),
    ("Coordenador de TI", "CC07", {1: 1}, (8500, 10500), 0.006, 4, (28, 48)),
    ("Analista de TI", "CC07", {1: 2}, (5000, 7000), 0.012, 6, (22, 40)),
    ("Gerente administrativo", "CC08", {1: 1}, (9000, 11000), 0.004, 1, (32, 55)),
    ("Assistente administrativo", "CC08", {1: 2, 2: 1, 3: 1}, (2200, 2900), 0.015, 2, (20, 40)),
    ("Recepcionista", "CC08", {1: 1, 2: 1, 3: 1}, (1800, 2200), 0.018, 0, (18, 35)),
]
CARGOS_MASCULINOS = {"Motorista entregador", "Ajudante de entrega", "Estoquista", "Conferente"}
CARGOS_FEMININOS = {"Recepcionista", "Assistente administrativo", "Assistente de departamento pessoal",
                    "Analista de RH"}
SAZONALIDADE_HE = [0.8, 0.85, 1.0, 0.95, 1.0, 1.0, 0.95, 1.0, 1.0, 1.05, 1.25, 1.6]
DISSIDIO = {2024: 1.05, 2025: 1.055}  # reajuste coletivo aplicado em maio
ENCARGOS = 0.35  # INSS patronal, RAT, terceiros e FGTS (simplificado)
BENEFICIO_MENSAL = 680.0


def nome_pessoa(sexo: str) -> str:
    primeiro = rng.choice(NOMES_M if sexo == "M" else NOMES_F)
    return f"{primeiro} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"


def novo_funcionario(cargo, filial: int, admissao: date, slot: int, inicial: bool, ref_idade: date) -> dict:
    nome_cargo, cc, _, (smin, smax), risco, he, (imin, imax) = cargo
    if nome_cargo in CARGOS_MASCULINOS:
        sexo = "M" if rng.random() < 0.9 else "F"
    elif nome_cargo in CARGOS_FEMININOS:
        sexo = "F" if rng.random() < 0.75 else "M"
    else:
        sexo = rng.choice("MF")
    if inicial:
        idade = rng.randint(imin, imax)
        anos_casa = (ref_idade - admissao).days / 365
        idade = max(idade, int(anos_casa) + imin)
        salario = smin + (smax - smin) * min(1.0, anos_casa / 8) * rng.uniform(0.6, 1.0)
    else:
        idade = imin + int(abs(rng.gauss(0, (imax - imin) / 3)))
        salario = smin * rng.uniform(1.0, 1.08)
    nascimento = date(ref_idade.year - idade, rng.randint(1, 12), rng.randint(1, 28))
    return dict(matricula=None, nome=nome_pessoa(sexo), sexo=sexo, nascimento=nascimento, cargo=nome_cargo,
                cc=cc, filial=filial, admissao=admissao, desligamento=None, motivo="",
                salario=round(salario, 2), risco_base=risco, he_base=he, slot=slot, cargo_def=cargo,
                insatisfacao=rng.random(), he_fator=rng.lognormvariate(0, 0.35))


def risco_de_saida(f: dict, ref: date, faixa_media: float) -> float:
    h = f["risco_base"]
    tempo = (ref - f["admissao"]).days
    if tempo < 90:
        h *= 2.2
    elif tempo < 365:
        h *= 1.4
    elif tempo > 5 * 365:
        h *= 0.6
    if f["salario"] < faixa_media:
        h *= 1.3
    if (ref - f["nascimento"]).days / 365.25 < 25:
        h *= 1.3
    h *= 0.4 + 1.6 * f["insatisfacao"]
    if f["he_base"] >= 14:
        h *= 0.8 + 0.4 * f["he_fator"]
    return min(h, 0.5)


def simular_rh():
    funcionarios, slots, vagas = [], {}, []
    faixa_media = {c[0]: sum(c[3]) / 2 for c in CARGOS}

    # Quadro existente em 01/01/2024
    for cargo in CARGOS:
        operacional = cargo[1] == "CC03"
        for filial, qtd in cargo[2].items():
            for _ in range(qtd):
                anos = min(14.0, rng.expovariate(1 / (2.0 if operacional else 4.0)))
                admissao = INICIO - timedelta(days=int(anos * 365) + rng.randint(1, 60))
                slot = len(slots) + 1
                f = novo_funcionario(cargo, filial, admissao, slot, True, INICIO)
                slots[slot] = [f]
                funcionarios.append(f)
    funcionarios.sort(key=lambda f: f["admissao"])
    for i, f in enumerate(funcionarios):
        f["matricula"] = str(1001 + i)
    proxima_matricula = 1001 + len(funcionarios)

    ponto, folha = [], defaultdict(lambda: defaultdict(float))
    for a, m in meses():
        ini, fim = date(a, m, 1), fim_do_mes(a, m)
        dias_mes = fim.day
        uteis_mes = sum(1 for d in datas(ini, fim) if dia_util(d))

        for vaga in [v for v in vagas if v["data"] <= fim]:
            vagas.remove(vaga)
            f = novo_funcionario(vaga["cargo"], vaga["filial"], vaga["data"], vaga["slot"], False, vaga["data"])
            f["matricula"] = str(proxima_matricula)
            proxima_matricula += 1
            slots[vaga["slot"]].append(f)
            funcionarios.append(f)

        if m == 5:
            for f in funcionarios:
                f["salario"] = round(f["salario"] * DISSIDIO[a], 2)
            for k in faixa_media:
                faixa_media[k] *= DISSIDIO[a]

        for f in funcionarios:
            if f["admissao"] > fim or (f["desligamento"] and f["desligamento"] < ini):
                continue
            inicio_f = max(ini, f["admissao"])
            if f["desligamento"] is None and inicio_f < fim:
                if rng.random() < risco_de_saida(f, inicio_f, faixa_media[f["cargo"]]):
                    saida = data_aleatoria(inicio_f + timedelta(days=1), fim)
                    tempo = (saida - f["admissao"]).days
                    if tempo < 90:
                        motivo = "Término do contrato de experiência" if rng.random() < 0.6 else "Pedido de demissão"
                    else:
                        sorteio = rng.random() - 0.25 * (f["insatisfacao"] - 0.5)
                        motivo = ("Pedido de demissão" if sorteio < 0.55 else
                                  "Dispensa sem justa causa" if sorteio < 0.95 else "Dispensa por justa causa")
                    f["desligamento"], f["motivo"] = saida, motivo
                    vagas.append(dict(cargo=f["cargo_def"], filial=f["filial"], slot=f["slot"],
                                      data=saida + timedelta(days=rng.randint(10, 45))))
            fim_f = min(fim, f["desligamento"]) if f["desligamento"] else fim
            uteis = sum(1 for d in datas(inicio_f, fim_f) if dia_util(d))
            if uteis == 0:
                continue
            proporcao = uteis / uteis_mes
            lam_faltas = 0.35 * (0.4 + 1.6 * f["insatisfacao"]) * (1.3 if f["cc"] == "CC03" else 1.0)
            faltas = min(uteis, poisson(lam_faltas * proporcao))
            atestado = min(uteis - faltas, rng.randint(1, 5)) if rng.random() < 0.07 else 0
            he = 0.0
            if f["he_base"]:
                he = f["he_base"] * f["he_fator"] * SAZONALIDADE_HE[m - 1] * proporcao * rng.lognormvariate(0, 0.3)
                he = round(he * 4) / 4
            ponto.append(dict(ano=a, mes=m, matricula=f["matricula"], nome=f["nome"], setor=NOME_CC[f["cc"]],
                              dias_trabalhados=uteis - faltas - atestado, faltas=faltas,
                              atestado_dias=atestado, horas_extras=he))

            dias_cal = (fim_f - inicio_f).days + 1
            bruto = (f["salario"] * dias_cal / dias_mes + f["salario"] / 220 * 1.5 * he
                     - f["salario"] / 30 * faltas)
            if f["desligamento"] and ini <= f["desligamento"] <= fim:
                bruto += f["salario"] * (1.6 if f["motivo"] == "Dispensa sem justa causa" else 0.8)
            chave = (a, m, f["cc"], f["filial"])
            folha[chave]["salarios"] += bruto
            folha[chave]["encargos"] += bruto * ENCARGOS
            folha[chave]["beneficios"] += BENEFICIO_MENSAL * dias_cal / dias_mes
    return funcionarios, slots, ponto, folha


def ocupante(slot_lista: list, d: date):
    for f in slot_lista:
        if f["admissao"] <= d and (f["desligamento"] is None or f["desligamento"] >= d):
            return f
    return None


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
TIPOS_CLIENTE = {
    "Supermercado": dict(peso=0.12, porte=3.0, freq=2.0, prazos=["28/56 dias", "28 dias"],
                         prefixos=["Supermercado", "Super", "Supermercados"]),
    "Mercado de bairro": dict(peso=0.34, porte=1.0, freq=1.0, prazos=["7 dias", "14 dias", "21 dias", "À vista"],
                              prefixos=["Mercado", "Minimercado", "Armazém", "Mercearia"]),
    "Restaurante": dict(peso=0.18, porte=0.7, freq=0.9, prazos=["7 dias", "14 dias"],
                        prefixos=["Restaurante", "Churrascaria", "Galeteria"]),
    "Padaria": dict(peso=0.12, porte=0.55, freq=1.0, prazos=["7 dias", "14 dias", "À vista"],
                    prefixos=["Padaria", "Panificadora", "Confeitaria"]),
    "Lanchonete": dict(peso=0.16, porte=0.4, freq=0.8, prazos=["À vista", "7 dias"],
                       prefixos=["Lanchonete", "Lancheria", "Bar e Lancheria"]),
    "Hotel": dict(peso=0.08, porte=0.9, freq=0.6, prazos=["14 dias", "28 dias"],
                  prefixos=["Hotel", "Pousada"]),
}
PREFERENCIA = {
    "Restaurante": {"Mercearia": 1.6, "Laticínios": 1.4, "Congelados": 1.5, "Higiene": 0.3, "Limpeza": 0.8},
    "Padaria": {"Laticínios": 2.0, "Mercearia": 1.4, "Higiene": 0.2, "Congelados": 0.8},
    "Lanchonete": {"Bebidas": 1.8, "Congelados": 1.6, "Higiene": 0.2, "Limpeza": 0.6},
    "Hotel": {"Higiene": 2.5, "Limpeza": 2.0, "Bebidas": 1.2, "Congelados": 0.6},
}
NOMES_FANTASIA = ["Bom Preço", "Avenida", "Central", "do Bairro", "Estrela", "Recanto", "Sabor do Sul",
                  "Querência", "Primavera", "São Jorge", "Bela Vista", "Nova Esperança", "Família",
                  "Ponto Certo", "Gaúcho", "Imigrante", "Colonial", "Boa Vista", "Santa Rita", "Progresso"]
N_CLIENTES = 420


def gerar_clientes(slots: dict) -> list[dict]:
    vendedores = defaultdict(list)
    for slot, lista in slots.items():
        if lista[0]["cargo"] == "Vendedor externo":
            vendedores[lista[0]["filial"]].append(slot)
    tipos = list(TIPOS_CLIENTE)
    clientes, usados = [], set()
    for filial in FILIAIS:
        for _ in range(round(N_CLIENTES * filial["peso"])):
            tipo = rng.choices(tipos, weights=[TIPOS_CLIENTE[t]["peso"] for t in tipos])[0]
            info = TIPOS_CLIENTE[tipo]
            while True:
                nome = f"{rng.choice(info['prefixos'])} {rng.choice(NOMES_FANTASIA + SOBRENOMES)}"
                if nome not in usados:
                    break
                nome = f"{nome} {rng.choice(SOBRENOMES)}"
                if nome not in usados:
                    break
            usados.add(nome)
            cidades = filial["cidades"]
            cidade = rng.choices(cidades, weights=[4] + [1] * (len(cidades) - 1))[0]
            if rng.random() < 0.8:
                cadastro = data_aleatoria(date(2012, 1, 1), date(2023, 12, 31))
            else:
                cadastro = data_aleatoria(INICIO, date(2025, 10, 31))
            inativacao = None
            if rng.random() < 0.12:
                inativacao = data_aleatoria(max(cadastro + timedelta(days=60), INICIO + timedelta(days=30)), FIM)
            porte = info["porte"] * rng.lognormvariate(0, 0.35)
            clientes.append(dict(
                razao_social=f"{nome} {rng.choice(['Ltda', 'ME', 'EIRELI', 'Ltda', 'Comércio de Alimentos Ltda'])}",
                cnpj=gerar_cnpj(), tipo=tipo, cidade=cidade, filial=filial["id"], cadastro=cadastro,
                inativacao=inativacao, bloqueio=None,
                perfil=rng.choices(["bom", "atrasa", "risco"], weights=[70, 22, 8])[0],
                prazo=rng.choice(info["prazos"]), porte=porte,
                freq=info["freq"] * rng.lognormvariate(0, 0.4),
                limite=round(porte * 15000, -3) or 5000.0,
                slot_vendedor=rng.choice(vendedores[filial["id"]])))
    clientes.sort(key=lambda c: c["cadastro"])
    for i, c in enumerate(clientes, start=1):
        c["cod"] = f"C{i:05d}"
    return clientes


def cliente_ativo(c: dict, d: date) -> bool:
    if c["cadastro"] > d:
        return False
    if c["inativacao"] and d >= c["inativacao"]:
        return False
    if c["bloqueio"] and d >= c["bloqueio"]:
        return False
    return True


# ---------------------------------------------------------------------------
# Demanda (pedidos de venda)
# ---------------------------------------------------------------------------
TAXA_PEDIDO = 0.105        # chance diária de um cliente médio fazer pedido
VALOR_LINHA = 720.0        # valor médio aproximado de um item de pedido de um cliente porte 1


def fator_evento(filial: int, d: date) -> float:
    """Queda de demanda na região metropolitana de Porto Alegre durante as enchentes de maio de 2024."""
    if filial == 1 and date(2024, 5, 3) <= d <= date(2024, 5, 31):
        return 0.45
    if filial == 1 and date(2024, 6, 1) <= d <= date(2024, 6, 20):
        return 0.8
    return 1.0


class Demanda:
    def __init__(self, produtos: list[dict]):
        self.produtos = produtos
        self._pesos = {}

    def pesos(self, tipo: str, mes: int) -> list[float]:
        chave = (tipo, mes)
        if chave not in self._pesos:
            pref = PREFERENCIA.get(tipo, {})
            acumulado, total = [], 0.0
            for p in self.produtos:
                total += p["popularidade"] * SAZONALIDADE_CATEGORIA[p["categoria"]][mes - 1] * pref.get(p["categoria"], 1.0)
                acumulado.append(total)
            self._pesos[chave] = acumulado
        return self._pesos[chave]

    def pedidos_do_dia(self, d: date, clientes: list[dict], r: random.Random) -> list[tuple[dict, list]]:
        anos = (d - INICIO).days / 365
        base = TAXA_PEDIDO * SAZONALIDADE_GERAL[d.month - 1] * (1 + 0.05 * anos) * (0.35 if d.weekday() == 5 else 1)
        pedidos, n_prod = [], len(self.produtos)
        for c in clientes:
            if not cliente_ativo(c, d):
                continue
            if r.random() >= min(0.9, base * c["freq"] * fator_evento(c["filial"], d)):
                continue
            n = min(15, 1 + poisson(2.6 * (1.7 if c["tipo"] == "Supermercado" else 1.0), r))
            pesos = self.pesos(c["tipo"], d.month)
            escolhidos = []
            for _ in range(n * 3):
                i = r.choices(range(n_prod), cum_weights=pesos)[0]
                if i not in escolhidos:
                    escolhidos.append(i)
                if len(escolhidos) == n:
                    break
            itens = []
            for i in escolhidos:
                preco = self.produtos[i]["preco"] * fator_preco(d)
                qtd = max(1, round(VALOR_LINHA * c["porte"] * r.lognormvariate(0, 0.5) / preco))
                itens.append((i, qtd))
            pedidos.append((c, itens))
        return pedidos


# ---------------------------------------------------------------------------
# Simulação da operação: vendas, estoque, compras e contas a receber
# ---------------------------------------------------------------------------
def parcelas(condicao: str) -> list[int]:
    if condicao == "À vista":
        return [0]
    if condicao == "28/56 dias":
        return [28, 56]
    return [int(condicao.split()[0])]


def ajustar_fim_de_semana(d: date) -> date:
    if d.weekday() == 5:
        return d + timedelta(days=2)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def simular_operacao(produtos, clientes, slots):
    demanda = Demanda(produtos)
    n_prod = len(produtos)

    # Estimativa inicial da demanda diária (como o comprador faria olhando o histórico)
    r_est = random.Random(SEED + 1)
    soma, dias_est = [0.0] * n_prod, 0
    for d in datas(INICIO, INICIO + timedelta(days=59)):
        if dia_de_venda(d):
            dias_est += 1
            for _, itens in demanda.pedidos_do_dia(d, clientes, r_est):
                for i, q in itens:
                    soma[i] += q
    media = [max(0.3, s / dias_est) for s in soma]

    estoque = [round(m * 30) for m in media]
    custo_medio = [p["custo"] for p in produtos]
    estoque_inicial = [(produtos[i]["cod"], estoque[i], custo_medio[i]) for i in range(n_prod)]
    transito = [0] * n_prod
    chegadas = defaultdict(list)       # data -> [(i, qtd, custo)]
    devolucoes = defaultdict(list)     # data -> [dict]
    proxima_nf = {f["id"]: 100001 for f in FILIAIS}
    proximo_pedido_compra = 50001

    supervisores = {}
    for slot, lista in slots.items():
        if lista[0]["cargo"] == "Supervisor de vendas":
            supervisores[lista[0]["filial"]] = slot

    vendas, compras, receber = [], [], []

    for d in datas(INICIO, FIM):
        for i, q, custo in chegadas.pop(d, []):
            custo_medio[i] = (estoque[i] * custo_medio[i] + q * custo) / (estoque[i] + q)
            estoque[i] += q
            transito[i] -= q

        if not dia_de_venda(d):
            continue

        for dev in devolucoes.pop(d, []):
            f = dev["filial"]
            dev["nf"] = proxima_nf[f]
            proxima_nf[f] += 1
            dev["data"] = d
            estoque[dev["produto"]] += dev["qtd"]
            vendas.append(dev)

        demanda_dia = [0] * n_prod
        for c, itens in demanda.pedidos_do_dia(d, clientes, rng):
            vendedor = (ocupante(slots[c["slot_vendedor"]], d)
                        or ocupante(slots[supervisores[c["filial"]]], d))
            cancelado = rng.random() < 0.015
            if c["tipo"] == "Supermercado":
                desconto = rng.choice([3, 4, 5, 6, 8])
            else:
                desconto = rng.choice([1, 2, 3, 5]) if rng.random() < 0.3 else 0
            linhas, total = [], 0.0
            for i, qtd in itens:
                demanda_dia[i] += qtd
                preco = round(produtos[i]["preco"] * fator_preco(d), 2)
                if cancelado:
                    faturado = qtd
                else:
                    faturado = min(qtd, max(estoque[i], 0))
                    estoque[i] -= faturado
                total += faturado * preco * (1 - desconto / 100)
                linhas.append(dict(produto=i, qtd_pedida=qtd, qtd=faturado, preco=preco,
                                   custo=round(custo_medio[i], 4)))
            if total == 0:
                continue
            f = c["filial"]
            nf = proxima_nf[f]
            proxima_nf[f] += 1
            for ln in linhas:
                vendas.append(dict(filial=f, nf=nf, data=d, cliente=c, vendedor=vendedor["matricula"],
                                   desconto=desconto, tipo="VENDA", nf_ref="",
                                   status="CANCELADO" if cancelado else "FATURADO", **ln))
                if not cancelado and ln["qtd"] > 0 and rng.random() < 0.007:
                    quando = d + timedelta(days=rng.randint(1, 10))
                    while not dia_de_venda(quando):
                        quando += timedelta(days=1)
                    if quando <= FIM:
                        devolvido = rng.randint(1, ln["qtd"])
                        devolucoes[quando].append(dict(
                            filial=f, nf=None, data=None, cliente=c, vendedor=vendedor["matricula"],
                            desconto=desconto, tipo="DEVOLUCAO", nf_ref=nf, status="FATURADO",
                            produto=ln["produto"], qtd_pedida=-devolvido, qtd=-devolvido,
                            preco=ln["preco"], custo=ln["custo"]))
            if not cancelado:
                receber.extend(titulos_a_receber(c, f, nf, d, round(total, 2)))

        # Reposição: compra quando estoque + pedidos em trânsito fica abaixo do ponto de pedido
        for i in range(n_prod):
            media[i] = 0.94 * media[i] + 0.06 * demanda_dia[i]
        pedidos_hoje = {}
        for i, p in enumerate(produtos):
            forn = p["fornecedor"]
            if estoque[i] + transito[i] >= media[i] * (forn["lead"] + 3):
                continue
            lote = max(1, round(media[i] * 21))
            if forn["cod"] not in pedidos_hoje:
                prevista = d + timedelta(days=forn["lead"])
                real = prevista + timedelta(days=0 if rng.random() < forn["pontualidade"] else rng.randint(1, 8))
                if real.weekday() == 6:
                    real += timedelta(days=1)
                pedidos_hoje[forn["cod"]] = dict(numero=proximo_pedido_compra, data=d, fornecedor=forn,
                                                  prevista=prevista, real=real, itens=[])
                proximo_pedido_compra += 1
            pc = pedidos_hoje[forn["cod"]]
            custo = round(p["custo"] * fator_preco(d) * forn["fator_custo"] * rng.uniform(0.98, 1.03), 2)
            pc["itens"].append((i, lote, custo))
            transito[i] += lote
            chegadas[pc["real"]].append((i, lote, custo))
        compras.extend(pedidos_hoje.values())

    return vendas, compras, receber, estoque_inicial


def titulos_a_receber(c: dict, filial: int, nf: int, emissao: date, total: float) -> list[dict]:
    prazos = parcelas(c["prazo"])
    valores = [round(total / len(prazos), 2)] * len(prazos)
    valores[-1] = round(total - sum(valores[:-1]), 2)
    titulos = []
    for n, (prazo, valor) in enumerate(zip(prazos, valores), start=1):
        vencimento = ajustar_fim_de_semana(emissao + timedelta(days=prazo))
        perfil = c["perfil"]
        sorteio = rng.random()
        if prazo == 0:
            pagamento = emissao
        elif perfil == "bom":
            pagamento = vencimento - timedelta(days=rng.randint(0, 2)) if sorteio < 0.85 else \
                vencimento + timedelta(days=rng.randint(1, 5))
        elif perfil == "atrasa":
            pagamento = vencimento if sorteio < 0.5 else vencimento + timedelta(days=int(rng.expovariate(1 / 15)) + 1)
        else:
            if sorteio < 0.30:
                pagamento = vencimento
            elif sorteio < 0.85:
                pagamento = vencimento + timedelta(days=int(rng.expovariate(1 / 35)) + 1)
            else:
                pagamento = None
                c["bloqueio"] = min(c["bloqueio"] or date.max, vencimento + timedelta(days=30))
        if pagamento:
            pagamento = max(emissao, ajustar_fim_de_semana(pagamento))
        atraso = (pagamento - vencimento).days if pagamento else 0
        pago = valor
        if atraso > 5 and rng.random() < 0.7:
            pago = round(valor * (1 + 0.02 + 0.01 * atraso / 30), 2)
        titulos.append(dict(titulo=f"{filial}-{nf}/{n}", nf=nf, filial=filial, cliente=c, emissao=emissao,
                            vencimento=vencimento, pagamento=pagamento, valor=valor, pago=pago, parcela=n,
                            parcelas=len(prazos)))
    return titulos


# ---------------------------------------------------------------------------
# Contas a pagar
# ---------------------------------------------------------------------------
def gerar_contas_a_pagar(compras, vendas, receber, folha, servico):
    titulos = []

    def titulo(forn, documento, descricao, conta, cc, filial, competencia, emissao, vencimento, valor,
               pode_atrasar=True):
        valor = round(valor, 2)
        vencimento = proximo_dia_util(vencimento)
        pagamento = vencimento
        chance = 0.15 if vencimento.month in (1, 2) else 0.06
        pago = valor
        if pode_atrasar and rng.random() < chance:
            atraso = rng.randint(2, 12)
            pagamento = proximo_dia_util(vencimento + timedelta(days=atraso))
            pago = round(valor * (1 + 0.02 + 0.01 * atraso / 30), 2)
        if pagamento > FIM:
            pagamento, pago = None, 0.0
        titulos.append(dict(fornecedor=forn, documento=documento, descricao=descricao, conta=conta, cc=cc,
                            filial=filial, competencia=competencia, emissao=emissao, vencimento=vencimento,
                            pagamento=pagamento, valor=valor, pago=pago))

    # Compras de mercadoria (vão para o estoque, não para a DRE)
    for pc in compras:
        if pc["real"] > FIM:
            continue
        forn = pc["fornecedor"]
        total = sum(q * c for _, q, c in pc["itens"])
        titulo(forn, f"NF {rng.randint(10000, 999999)}", f"Compra de mercadorias - pedido {pc['numero']}",
               "1.05", "CC06", 1, (pc["real"].year, pc["real"].month), pc["real"],
               pc["real"] + timedelta(days=forn["prazo"]), total)

    # Bases mensais vindas da operação
    receita_mes = defaultdict(float)
    notas = set()
    for v in vendas:
        if v["status"] != "FATURADO":
            continue
        chave = (v["data"].year, v["data"].month)
        receita_mes[chave] += v["qtd"] * v["preco"] * (1 - v["desconto"] / 100)
        if v["tipo"] == "VENDA":
            notas.add((chave, v["filial"], v["nf"]))
    entregas_mes = defaultdict(int)
    for chave, filial, _ in notas:
        entregas_mes[(chave, filial)] += 1
    recebido_mes = defaultdict(float)
    for t in receber:
        if t["pagamento"]:
            recebido_mes[(t["pagamento"].year, t["pagamento"].month)] += t["pago"]

    aluguel = {1: 38000.0, 2: 16000.0, 3: 12000.0}
    energia = {1: 9200.0, 2: 4300.0, 3: 3100.0}
    facilities = {1: 7800.0, 2: 3900.0, 3: 3200.0}
    for a, m in meses():
        comp = (a, m)
        ini = date(a, m, 1)
        fim = fim_do_mes(a, m)
        pa, pm = mes_seguinte(a, m)
        ref = f"{m:02d}/{a}"
        verao = m in (12, 1, 2, 3)
        reaj = 1.045 if a == 2025 else 1.0
        for fid, f in FILIAL.items():
            nome = f["nome"]
            titulo(servico["aluguel"], f"Boleto {a}{m:02d}{fid}", f"Aluguel - {nome} - {ref}", "5.04", "CC08",
                   fid, comp, ini, date(a, m, 5), aluguel[fid] * reaj, pode_atrasar=False)
            titulo(servico["energia"], f"Fatura {rng.randint(1000000, 9999999)}", f"Energia elétrica e água - {nome} - {ref}",
                   "5.05", "CC08", fid, comp, fim, date(pa, pm, 12),
                   energia[fid] * (1.25 if verao else 1.0) * rng.uniform(0.92, 1.1) * reaj)
            titulo(servico["escritorio"], f"NF {rng.randint(1000, 99999)}", f"Material de escritório - {nome}",
                   "5.06", "CC08", fid, comp, data_aleatoria(ini, fim), fim + timedelta(days=14),
                   rng.uniform(700, 2600) * (0.6 if fid > 1 else 1.0))
            titulo(servico["facilities"], f"NF {rng.randint(1000, 99999)}", f"Limpeza e vigilância - {nome} - {ref}",
                   "5.07", "CC08", fid, comp, fim, date(pa, pm, 10), facilities[fid] * reaj)
            titulo(servico["internet"], f"Fatura {rng.randint(100000, 999999)}", f"Internet e telefonia - {nome} - {ref}",
                   "5.08", "CC07", fid, comp, fim, date(pa, pm, 15), (1450.0 if fid == 1 else 690.0) * reaj)
            n_entregas = entregas_mes.get((comp, fid), 0)
            combustivel = n_entregas * 46.0 * (1.07 if a == 2025 else 1.0) * rng.uniform(0.93, 1.1)
            for quinzena, emissao in ((1, date(a, m, 15)), (2, fim)):
                titulo(servico["combustivel"], f"NF {rng.randint(10000, 999999)}",
                       f"Combustível frota - {nome} - {quinzena}ª quinzena {ref}", "5.09", "CC03", fid, comp,
                       emissao, emissao + timedelta(days=10), combustivel / 2)
            for _ in range(poisson(1.6 if fid == 1 else 0.9)):
                titulo(servico["manutencao"], f"NF {rng.randint(1000, 99999)}", f"Manutenção de veículo - {nome}",
                       "5.10", "CC03", fid, comp, data_aleatoria(ini, fim), fim + timedelta(days=15),
                       rng.lognormvariate(math.log(1900), 0.6))
            for cc in NOME_CC:
                base = folha.get((a, m, cc, fid))
                if not base:
                    continue
                titulo(servico["folha"], f"Folha {ref}", f"Salários {NOME_CC[cc]} - {nome} - {ref}", "5.01", cc,
                       fid, comp, fim, date(pa, pm, 5), base["salarios"], pode_atrasar=False)
                titulo(servico["encargos"], f"Guias {ref}", f"INSS/FGTS {NOME_CC[cc]} - {nome} - {ref}", "5.02",
                       cc, fid, comp, fim, date(pa, pm, 20), base["encargos"], pode_atrasar=False)
                titulo(servico["beneficios"], f"Pedido VR/VT {ref}", f"Benefícios {NOME_CC[cc]} - {nome} - {ref}",
                       "5.03", cc, fid, comp, ini - timedelta(days=5), ini, base["beneficios"], pode_atrasar=False)

        titulo(servico["contabilidade"], f"NF {rng.randint(1000, 9999)}", f"Honorários contábeis - {ref}", "5.07",
               "CC04", 1, comp, fim, date(pa, pm, 10), 9500.0 * reaj)
        titulo(servico["juridico"], f"NF {rng.randint(1000, 9999)}", f"Assessoria jurídica - {ref}", "5.07",
               "CC01", 1, comp, fim, date(pa, pm, 10), 3800.0 * reaj)
        titulo(servico["erp"], f"NF {rng.randint(1000, 9999)}", f"Licença do ERP e suporte - {ref}", "5.08",
               "CC07", 1, comp, ini, date(a, m, 20), 6900.0 * reaj)
        if rng.random() < 0.25:
            titulo(servico["escritorio"], f"NF {rng.randint(1000, 99999)}", "Compra de equipamentos de informática",
                   "5.08", "CC07", 1, comp, data_aleatoria(ini, fim), fim + timedelta(days=28),
                   rng.uniform(4000, 18000))
        marketing = 4200.0 + (16000.0 if m in (11, 12) else 0) + (6000.0 if m == 3 else 0)
        titulo(servico["marketing"], f"NF {rng.randint(1000, 9999)}", f"Campanhas e material de trade - {ref}",
               "5.11", "CC02", 1, comp, fim, date(pa, pm, 15), marketing * rng.uniform(0.9, 1.15))
        titulo(servico["banco"], f"Extrato {ref}", f"Tarifas bancárias e cobrança - {ref}", "6.01", "CC04", 1,
               comp, fim, fim, 1200.0 + 0.0012 * recebido_mes.get(comp, 0), pode_atrasar=False)
        receita = receita_mes.get(comp, 0)
        titulo(servico["icms"], f"GA {ref}", f"ICMS apurado - {ref}", "3.03", "CC04", 1, comp, fim,
               date(pa, pm, 20), receita * 0.105, pode_atrasar=False)
        titulo(servico["federal"], f"DARF {ref}", f"PIS/COFINS apurado - {ref}", "3.03", "CC04", 1, comp, fim,
               date(pa, pm, 25), receita * 0.0365, pode_atrasar=False)
    return titulos


# ---------------------------------------------------------------------------
# Orçamento (feito "antes" de cada ano, com vieses de propósito)
# ---------------------------------------------------------------------------
VIES_ORCAMENTO = {"3.01": 1.04, "3.02": 0.8, "4.01": 1.03, "5.09": 0.86, "5.10": 0.78, "5.11": 1.15,
                  "5.05": 0.95, "5.01": 0.98}


def gerar_orcamento(vendas, pagar):
    real = defaultdict(float)
    for v in vendas:
        if v["status"] != "FATURADO":
            continue
        a, m = v["data"].year, v["data"].month
        valor = v["qtd"] * v["preco"] * (1 - v["desconto"] / 100)
        if v["tipo"] == "VENDA":
            real[(a, "3.01", "CC02", m)] += valor
        else:
            real[(a, "3.02", "CC02", m)] += -valor
        real[(a, "4.01", "CC02", m)] += v["qtd"] * v["custo"]
    for t in pagar:
        if t["conta"] == "1.05":
            continue
        a, m = t["competencia"]
        real[(a, t["conta"], t["cc"], m)] += t["valor"]
    linhas = defaultdict(lambda: [0.0] * 12)
    for (a, conta, cc, m), valor in real.items():
        vies = VIES_ORCAMENTO.get(conta, 1.0) * (0.98 if a == 2025 else 1.0)
        linhas[(a, conta, cc)][m - 1] = round(valor * vies * rng.gauss(1, 0.04), -2)
    return linhas


# ---------------------------------------------------------------------------
# Gravação dos arquivos (com os problemas de qualidade injetados)
# ---------------------------------------------------------------------------
def salvar_csv(df: pd.DataFrame, caminho: Path, encoding: str = "cp1252"):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, sep=";", index=False, encoding=encoding)


def gravar_cadastros():
    salvar_csv(pd.DataFrame([dict(id_filial=f["id"], nome=f["nome"], cidade=f["cidade"], uf="RS") for f in FILIAIS]),
               BRUTO / "cadastros" / "filiais.csv", "utf-8-sig")
    salvar_csv(pd.DataFrame(CENTROS_CUSTO, columns=["cod_centro_custo", "nome"]),
               BRUTO / "cadastros" / "centros_custo.csv", "utf-8-sig")
    salvar_csv(pd.DataFrame(PLANO_CONTAS, columns=["cod_conta", "descricao", "grupo_dre"]),
               BRUTO / "cadastros" / "plano_contas.csv", "utf-8-sig")


def gravar_produtos_fornecedores(produtos, fornecedores, estoque_inicial):
    variantes = {"Bebidas": ["BEBIDAS", "bebida"], "Laticínios": ["Laticinios", "LATICÍNIOS"],
                 "Limpeza": ["limpeza"], "Higiene": ["Higiene pessoal"], "Mercearia": ["MERCEARIA"],
                 "Congelados": ["Congelado"]}
    linhas = []
    for p in produtos:
        categoria = p["categoria"]
        if rng.random() < 0.15:
            categoria = rng.choice(variantes[categoria])
        linhas.append({"Código": p["cod"], "Descrição": p["descricao"], "Categoria": categoria,
                       "Unidade": p["unidade"], "Fornecedor principal": p["fornecedor"]["cod"],
                       "Preço tabela jan/2024": p["preco"], "Ativo": "S"})
    caminho = BRUTO / "compras" / "cadastro_produtos.xlsx"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_excel(caminho, index=False, sheet_name="Produtos")

    linhas = []
    for f in fornecedores:
        linhas.append(dict(cod_fornecedor=f["cod"], razao_social=f["razao_social"],
                           cnpj=mascarar_cnpj(f["cnpj"]) if rng.random() < 0.6 else f["cnpj"],
                           tipo=f["tipo"], cidade=f["cidade"], prazo_pagamento_dias=f["prazo"] or "",
                           lead_time_dias=f["lead"] or ""))
    salvar_csv(pd.DataFrame(linhas), BRUTO / "erp" / "fornecedores.csv")
    salvar_csv(pd.DataFrame([dict(cod_produto=c, quantidade=q, custo_medio=dec(cm, 4), data_posicao="01/01/2024")
                             for c, q, cm in estoque_inicial]), BRUTO / "erp" / "estoque_inicial.csv")


def gravar_clientes(clientes, vendas, receber):
    variacoes_cidade = {"Porto Alegre": ["POA", "Porto alegre", "PORTO ALEGRE"],
                        "Caxias do Sul": ["Caxias", "CAXIAS DO SUL"], "Pelotas": ["PELOTAS", "pelotas"],
                        "São Leopoldo": ["Sao Leopoldo"], "Gravataí": ["Gravatai"]}
    linhas = []
    for c in clientes:
        cidade = c["cidade"]
        if cidade in variacoes_cidade and rng.random() < 0.2:
            cidade = rng.choice(variacoes_cidade[cidade])
        razao = c["razao_social"]
        sorteio = rng.random()
        if sorteio < 0.08:
            razao = razao.upper()
        elif sorteio < 0.14:
            razao = f" {razao}  "
        linhas.append(dict(cod_cliente=c["cod"], razao_social=razao,
                           cnpj=mascarar_cnpj(c["cnpj"]) if rng.random() < 0.5 else c["cnpj"],
                           tipo_cliente=c["tipo"], cidade=cidade, uf="RS", id_filial=c["filial"],
                           data_cadastro=br_data(c["cadastro"]), condicao_pagamento=c["prazo"],
                           limite_credito=dec(c["limite"]),
                           situacao="INATIVO" if c["inativacao"] or c["bloqueio"] else "ATIVO"))

    # Cadastro duplicado: o mesmo CNPJ ganhou um segundo código e as vendas seguintes usam o novo
    candidatos = [c for c in clientes if c["cadastro"] < date(2023, 6, 1) and not c["inativacao"]]
    for i, c in enumerate(rng.sample(candidatos, 4)):
        novo = f"C{len(clientes) + i + 1:05d}"
        corte = data_aleatoria(date(2024, 6, 1), date(2025, 3, 1))
        linhas.append(dict(linhas[clientes.index(c)], cod_cliente=novo,
                           razao_social=c["razao_social"].upper(), data_cadastro=br_data(corte)))
        for v in vendas:
            if v["cliente"] is c and v["data"] >= corte:
                v["cod_cliente_override"] = novo
        for t in receber:
            if t["cliente"] is c and t["emissao"] >= corte:
                t["cod_cliente_override"] = novo
    salvar_csv(pd.DataFrame(linhas), BRUTO / "erp" / "clientes.csv")


def gravar_vendas(vendas, produtos):
    linhas = []
    for v in vendas:
        cod_produto = produtos[v["produto"]]["cod"]
        if rng.random() < 0.004:
            cod_produto = f" {cod_produto.lower()}"
        preco = v["preco"]
        linhas.append(dict(serie=v["filial"], nf_numero=v["nf"], data_emissao=br_data(v["data"]),
                           cod_cliente=v.get("cod_cliente_override", v["cliente"]["cod"]),
                           cod_vendedor=v["vendedor"], cod_produto=cod_produto,
                           qtd_pedida=v["qtd_pedida"], qtd_faturada=v["qtd"], preco_unitario=preco,
                           desconto_pct=dec(v["desconto"], 1), custo_medio_unitario=v["custo"],
                           tipo_operacao=v["tipo"], nf_referencia=v["nf_ref"], status=v["status"]))
    # Preço digitado sem a vírgula em alguns itens
    for linha in rng.sample(linhas, 6):
        linha["preco_unitario"] = round(linha["preco_unitario"] * 100, 2)
    for linha in linhas:
        linha["preco_unitario"] = dec(linha["preco_unitario"])
        linha["custo_medio_unitario"] = dec(linha["custo_medio_unitario"], 4)
    # Linhas exportadas em duplicidade
    for linha in rng.sample(linhas, round(len(linhas) * 0.003)):
        linhas.append(dict(linha))
    linhas.sort(key=lambda x: (x["data_emissao"][6:] + x["data_emissao"][3:5] + x["data_emissao"][:2],
                               x["serie"], x["nf_numero"]))
    salvar_csv(pd.DataFrame(linhas), BRUTO / "erp" / "vendas_itens.csv")


def gravar_compras(compras, produtos):
    linhas = []
    for pc in compras:
        aberto = pc["real"] > FIM
        for i, q, custo in pc["itens"]:
            linhas.append(dict(pedido_numero=pc["numero"], data_pedido=br_data(pc["data"]),
                               cod_fornecedor=pc["fornecedor"]["cod"], cod_produto=produtos[i]["cod"],
                               quantidade=q, custo_unitario=dec(custo),
                               data_entrega_prevista=br_data(pc["prevista"]),
                               data_entrega_real="" if aberto else br_data(pc["real"]),
                               status="EM ABERTO" if aberto else "ENTREGUE"))
    salvar_csv(pd.DataFrame(linhas), BRUTO / "erp" / "pedidos_compra.csv")


def gravar_receber(receber):
    linhas = []
    for t in receber:
        pagamento = t["pagamento"] if t["pagamento"] and t["pagamento"] <= FIM else None
        if pagamento:
            status = "PAGO"
        elif t["vencimento"] > FIM:
            status = "A VENCER"
        else:
            status = "VENCIDO"
        linhas.append(dict(titulo=t["titulo"], serie=t["filial"], nf_numero=t["nf"],
                           cod_cliente=t.get("cod_cliente_override", t["cliente"]["cod"]),
                           parcela=f"{t['parcela']}/{t['parcelas']}", data_emissao=br_data(t["emissao"]),
                           data_vencimento=br_data(t["vencimento"]), data_pagamento=br_data(pagamento),
                           valor=dec(t["valor"]), valor_pago=dec(t["pago"]) if pagamento else "", status=status))
    # Ano digitado errado na baixa: pagamento "antes" da emissão
    pagos_2025 = [ln for ln in linhas if ln["data_pagamento"].endswith("2025") and ln["data_emissao"].endswith("2025")]
    for ln in rng.sample(pagos_2025, 12):
        ln["data_pagamento"] = ln["data_pagamento"][:6] + "2024"
    salvar_csv(pd.DataFrame(linhas), BRUTO / "financeiro" / "contas_receber.csv")


def gravar_pagar(pagar):
    linhas = []
    for n, t in enumerate(sorted(pagar, key=lambda t: (t["emissao"], t["fornecedor"]["cod"])), start=1):
        iso = rng.random() < 0.15

        def fmt(d):
            if not d:
                return ""
            return d.isoformat() if iso else br_data(d)

        cnpj = t["fornecedor"]["cnpj"]
        linhas.append({"ID": n, "Fornecedor": t["fornecedor"]["razao_social"],
                       "CNPJ": mascarar_cnpj(cnpj) if rng.random() < 0.5 else cnpj,
                       "Documento": t["documento"], "Descrição": t["descricao"], "Conta contábil": t["conta"],
                       "Centro de custo": "" if rng.random() < 0.03 else t["cc"], "Filial": t["filial"],
                       "Competência": f"{t['competencia'][1]:02d}/{t['competencia'][0]}",
                       "Emissão": fmt(t["emissao"]), "Vencimento": fmt(t["vencimento"]),
                       "Pagamento": fmt(t["pagamento"]), "Valor": reais(t["valor"]),
                       "Valor pago": reais(t["pago"]) if t["pagamento"] else ""})
    salvar_csv(pd.DataFrame(linhas), BRUTO / "financeiro" / "contas_pagar.csv")


def gravar_orcamento(linhas_orc):
    caminho = BRUTO / "financeiro" / "orcamento.xlsx"
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    descricao = {c: d for c, d, _ in PLANO_CONTAS}
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        for ano in (2024, 2025):
            dados = []
            for (a, conta, cc), valores in sorted(linhas_orc.items()):
                if a != ano:
                    continue
                dados.append({"Conta": conta, "Descrição": descricao[conta], "Centro de custo": cc,
                              **dict(zip(nomes_meses, valores)), "Total": round(sum(valores), 2)})
            aba = f"Orçamento {ano}"
            pd.DataFrame(dados).to_excel(writer, sheet_name=aba, index=False, startrow=3)
            ws = writer.sheets[aba]
            ws["A1"] = f"Distribuidora Sul Ltda. - Orçamento anual {ano} (valores em R$)"
            ws["A2"] = f"Controladoria - versão aprovada pela diretoria em 15/12/{ano - 1}"


def gravar_rh(funcionarios, ponto):
    variantes = {"Logística": ["Logistica", "LOGÍSTICA"], "Comercial": ["COMERCIAL", "Vendas"],
                 "Administrativo": ["Adm", "ADMINISTRATIVO"], "Financeiro": ["Financeiro "]}
    linhas = []
    for f in sorted(funcionarios, key=lambda f: int(f["matricula"])):
        setor = NOME_CC[f["cc"]]
        if setor in variantes and rng.random() < 0.15:
            setor = rng.choice(variantes[setor])
        linhas.append({"Matrícula": int(f["matricula"]), "Nome": f["nome"], "Sexo": f["sexo"],
                       "Data de nascimento": None if rng.random() < 0.05 else f["nascimento"],
                       "Cargo": f["cargo"], "Setor": setor, "Filial": FILIAL[f["filial"]]["nome"],
                       "Admissão": f["admissao"], "Desligamento": f["desligamento"],
                       "Motivo do desligamento": f["motivo"], "Salário atual": reais(f["salario"])})
    caminho = BRUTO / "rh" / "funcionarios.xlsx"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_excel(caminho, index=False, sheet_name="Quadro")

    por_mes = defaultdict(list)
    for p in ponto:
        por_mes[(p["ano"], p["mes"])].append(p)
    for (a, m), registros in por_mes.items():
        layout_novo = (a, m) >= (2025, 3)  # o RH trocou a planilha modelo em março de 2025
        linhas = []
        for p in sorted(registros, key=lambda p: int(p["matricula"])):
            horas = int(p["horas_extras"])
            minutos = round((p["horas_extras"] - horas) * 60)
            he = f"{horas:02d}:{minutos:02d}"
            if layout_novo:
                linhas.append({"Matrícula": p["matricula"], "Nome do colaborador": p["nome"], "Setor": p["setor"],
                               "HE (hh:mm)": he, "Faltas": p["faltas"], "Atestados (dias)": p["atestado_dias"],
                               "Dias trab.": p["dias_trabalhados"]})
            else:
                linhas.append(dict(matricula=p["matricula"], nome=p["nome"], setor=p["setor"],
                                   dias_trabalhados=p["dias_trabalhados"], faltas=p["faltas"],
                                   atestado_dias=p["atestado_dias"], horas_extras=he))
        salvar_csv(pd.DataFrame(linhas), BRUTO / "rh" / "ponto" / f"ponto_{a}_{m:02d}.csv", "utf-8-sig")


def main():
    print("Gerando cadastros, produtos e fornecedores...")
    fornecedores, produtos, servico = gerar_fornecedores_e_produtos()
    print("Simulando RH (quadro, rotatividade, ponto e folha)...")
    funcionarios, slots, ponto, folha = simular_rh()
    clientes = gerar_clientes(slots)
    print("Simulando vendas, estoque e compras dia a dia...")
    vendas, compras, receber, estoque_inicial = simular_operacao(produtos, clientes, slots)
    print("Gerando contas a pagar e orçamento...")
    pagar = gerar_contas_a_pagar(compras, vendas, receber, folha, servico)
    orcamento = gerar_orcamento(vendas, pagar)

    print("Gravando arquivos em", BRUTO)
    gravar_cadastros()
    gravar_produtos_fornecedores(produtos, fornecedores, estoque_inicial)
    gravar_clientes(clientes, vendas, receber)
    gravar_vendas(vendas, produtos)
    gravar_compras(compras, produtos)
    gravar_receber(receber)
    gravar_pagar(pagar)
    gravar_orcamento(orcamento)
    gravar_rh(funcionarios, ponto)

    notas = {(v["filial"], v["nf"]) for v in vendas if v["tipo"] == "VENDA"}
    receita = sum(v["qtd"] * v["preco"] * (1 - v["desconto"] / 100) for v in vendas if v["status"] == "FATURADO")
    print(f"  {len(clientes)} clientes, {len(produtos)} produtos, {len(fornecedores)} fornecedores")
    print(f"  {len(funcionarios)} funcionários no histórico, {len(notas)} notas, {len(vendas)} itens de venda")
    print(f"  {len(compras)} pedidos de compra, {len(receber)} títulos a receber, {len(pagar)} títulos a pagar")
    print(f"  Receita líquida de devoluções no período: R$ {receita:,.0f}")


if __name__ == "__main__":
    main()
