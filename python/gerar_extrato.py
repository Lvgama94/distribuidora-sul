"""
Gera o extrato bancário de dezembro/2025 da conta movimento da Distribuidora Sul,
a partir dos títulos recebidos e pagos no mês (data/tratado), com as diferenças
típicas que uma conciliação bancária precisa encontrar:

- tarifas e IOF debitados pelo banco e não lançados no contas a pagar;
- pagamentos lançados no sistema nos últimos dias do mês que só compensaram em janeiro;
- clientes que pagaram juros não lançados (valor diferente do título);
- PIX recebidos sem identificação do título (só dá para casar por data e valor).

Uso:   python python/gerar_extrato.py
Saída: data/bruto/financeiro/extrato_bancario_2025_12.csv (formato de exportação do banco)
"""
import random
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TRATADO = RAIZ / "data" / "tratado"
SAIDA = RAIZ / "data" / "bruto" / "financeiro" / "extrato_bancario_2025_12.csv"
INICIO, FIM = pd.Timestamp("2025-12-01"), pd.Timestamp("2025-12-31")
SALDO_INICIAL = 1_250_000.00

rng = random.Random(1225)


def historico_pagamento(conta: str) -> str:
    if conta in ("5.01", "5.03"):
        return "PAGAMENTO FOLHA/BENEFICIOS"
    if conta in ("3.03", "5.02"):
        return "PAGAMENTO TRIBUTOS"
    if conta == "6.01":
        return "TARIFAS BANCARIAS"
    return "PAGAMENTO BOLETO"


def main():
    receber = pd.read_csv(TRATADO / "conta_receber.csv", parse_dates=["data_pagamento"])
    pagar = pd.read_csv(TRATADO / "conta_pagar.csv", parse_dates=["data_pagamento"])
    recebidos = receber[receber.data_pagamento.between(INICIO, FIM)]
    pagos = pagar[pagar.data_pagamento.between(INICIO, FIM)]

    movimentos = []
    for r in recebidos.itertuples():
        movimentos.append(dict(data=r.data_pagamento, historico="LIQUIDACAO DE BOLETO", documento=r.titulo,
                               valor=round(r.valor_pago, 2)))
    for p in pagos.itertuples():
        movimentos.append(dict(data=p.data_pagamento, historico=historico_pagamento(p.cod_conta),
                               documento=f"CP{p.id_titulo}", valor=-round(p.valor_pago, 2)))

    # Pagamentos lançados nos últimos dias do mês que o banco só compensou em janeiro
    fim_de_mes = [m for m in movimentos if m["documento"].startswith("CP") and m["data"] >= pd.Timestamp("2025-12-29")]
    for m in rng.sample(fim_de_mes, min(4, len(fim_de_mes))):
        movimentos.remove(m)

    # PIX recebidos sem identificação do título
    boletos = [m for m in movimentos if m["historico"] == "LIQUIDACAO DE BOLETO"]
    for m in rng.sample(boletos, 15):
        m.update(historico="PIX RECEBIDO", documento="")

    # Clientes que pagaram juros não lançados no sistema
    for m in rng.sample([m for m in boletos if m["documento"]], 3):
        m["valor"] = round(m["valor"] + rng.uniform(8, 60), 2)

    # Tarifas e IOF que só existem no banco
    for dia, historico, valor in [(5, "TARIFA PACOTE DE SERVICOS", -189.90), (12, "TARIFA TED", -12.50),
                                  (19, "TARIFA TED", -12.50), (31, "IOF", -3.27)]:
        movimentos.append(dict(data=pd.Timestamp(2025, 12, dia), historico=historico, documento="", valor=valor))

    extrato = pd.DataFrame(movimentos).sort_values(["data", "valor"], ascending=[True, False]).reset_index(drop=True)
    extrato["saldo"] = (SALDO_INICIAL + extrato.valor.cumsum()).round(2)
    saida = pd.DataFrame({
        "Data": extrato.data.dt.strftime("%d/%m/%Y"),
        "Histórico": extrato.historico,
        "Documento": extrato.documento,
        "Valor": extrato.valor.map(lambda v: f"{v:.2f}".replace(".", ",")),
        "Saldo": extrato.saldo.map(lambda v: f"{v:.2f}".replace(".", ",")),
    })
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    saida.to_csv(SAIDA, sep=";", index=False, encoding="cp1252")
    print(f"{len(saida)} lançamentos no extrato | saldo final R$ {extrato.saldo.iloc[-1]:,.2f}")
    print(f"Títulos do sistema no mês: {len(recebidos)} recebidos e {len(pagos)} pagos")


if __name__ == "__main__":
    main()
