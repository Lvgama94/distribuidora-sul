// Títulos baixados no sistema no período: recebimentos (contas a receber) e pagamentos (contas a pagar).
// Pagamentos entram com valor negativo, como no extrato.
let
    Pasta = Excel.CurrentWorkbook(){[Name = "PastaDados"]}[Content]{0}[Column1],
    Inicio = Date.From(Excel.CurrentWorkbook(){[Name = "DataInicio"]}[Content]{0}[Column1]),
    Fim = Date.From(Excel.CurrentWorkbook(){[Name = "DataFim"]}[Content]{0}[Column1]),
    LerCsv = (arquivo as text) as table =>
        Table.PromoteHeaders(
            Csv.Document(File.Contents(Pasta & "tratado\" & arquivo), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            [PromoteAllScalars = true]),
    NoPeriodo = (t as table) as table =>
        let
            SemVazios = Table.ReplaceValue(t, "", null, Replacer.ReplaceValue, {"data_pagamento", "valor_pago"}),
            Tipos = Table.TransformColumnTypes(SemVazios, {{"data_pagamento", type date}, {"valor_pago", type number}}, "en-US")
        in
            Table.SelectRows(Tipos, each [data_pagamento] <> null and [data_pagamento] >= Inicio and [data_pagamento] <= Fim),

    Recebidos = NoPeriodo(LerCsv("conta_receber.csv")),
    Recebimentos = Table.FromRecords(Table.TransformRows(Recebidos, each [
        Documento = [titulo], Data = [data_pagamento], Valor = [valor_pago],
        Descrição = "Recebimento do cliente " & [cod_cliente], Tipo = "Recebimento"])),

    Pagos = NoPeriodo(LerCsv("conta_pagar.csv")),
    Pagamentos = Table.FromRecords(Table.TransformRows(Pagos, each [
        Documento = "CP" & [id_titulo], Data = [data_pagamento], Valor = -[valor_pago],
        Descrição = [descricao], Tipo = "Pagamento"])),

    Juntos = Table.Combine({Recebimentos, Pagamentos}),
    Tipos = Table.TransformColumnTypes(Juntos,
        {{"Documento", type text}, {"Data", type date}, {"Valor", type number}, {"Descrição", type text}, {"Tipo", type text}})
in
    Tipos
