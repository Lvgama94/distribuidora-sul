// Extrato exportado do banco (CSV com ponto e vírgula, vírgula decimal e acentos em Windows-1252).
let
    Pasta = Excel.CurrentWorkbook(){[Name = "PastaDados"]}[Content]{0}[Column1],
    Arquivo = Excel.CurrentWorkbook(){[Name = "ArquivoExtrato"]}[Content]{0}[Column1],
    Fonte = Csv.Document(File.Contents(Pasta & "bruto\financeiro\" & Arquivo),
        [Delimiter = ";", Encoding = 1252, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    SemVazios = Table.ReplaceValue(Cabecalho, "", null, Replacer.ReplaceValue, {"Documento"}),
    Tipos = Table.TransformColumnTypes(SemVazios,
        {{"Data", type date}, {"Histórico", type text}, {"Documento", type text}, {"Valor", type number}, {"Saldo", type number}},
        "pt-BR")
in
    Tipos
