// Consolida os arquivos mensais de ponto do RH (data/bruto/rh/ponto/ponto_AAAA_MM.csv) numa tabela só.
// O RH trocou o modelo da planilha em mar/2025: colunas com outros nomes e em outra ordem.
// A pasta vem da célula "PastaPonto" (aba Configuração), então funciona em qualquer computador.
let
    Pasta = Excel.CurrentWorkbook(){[Name = "PastaPonto"]}[Content]{0}[Column1],
    Arquivos = Folder.Files(Pasta),
    SoPonto = Table.SelectRows(Arquivos, each Text.StartsWith([Name], "ponto_") and [Extension] = ".csv"),

    // Competência a partir do nome do arquivo: ponto_2025_03.csv -> 01/03/2025
    ComCompetencia = Table.AddColumn(SoPonto, "Competência", each
        let partes = Text.Split(Text.BeforeDelimiter([Name], "."), "_")
        in #date(Number.From(partes{1}), Number.From(partes{2}), 1), type date),

    // Lê cada CSV e traz o layout novo para os nomes do layout antigo
    Lidos = Table.AddColumn(ComCompetencia, "Dados", each
        Table.RenameColumns(
            Table.PromoteHeaders(Csv.Document([Content], [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
                [PromoteAllScalars = true]),
            {{"Matrícula", "matricula"}, {"Nome do colaborador", "nome"}, {"Setor", "setor"},
             {"HE (hh:mm)", "horas_extras"}, {"Faltas", "faltas"}, {"Atestados (dias)", "atestado_dias"},
             {"Dias trab.", "dias_trabalhados"}},
            MissingField.Ignore)),
    Selecionado = Table.SelectColumns(Lidos, {"Competência", "Name", "Dados"}),
    Expandido = Table.ExpandTableColumn(Selecionado, "Dados",
        {"matricula", "nome", "setor", "dias_trabalhados", "faltas", "atestado_dias", "horas_extras"},
        {"Matrícula", "Nome", "Setor", "Dias Trabalhados", "Faltas", "Dias de Atestado", "HE (hh:mm)"}),

    // "12:30" -> 12,5 horas
    Horas = Table.AddColumn(Expandido, "Horas Extras", each
        let p = Text.Split([#"HE (hh:mm)"], ":") in Number.From(p{0}) + Number.From(p{1}) / 60, type number),
    Tipos = Table.TransformColumnTypes(Horas, {{"Matrícula", Int64.Type}, {"Dias Trabalhados", Int64.Type},
        {"Faltas", Int64.Type}, {"Dias de Atestado", Int64.Type}}),
    Previstos = Table.AddColumn(Tipos, "Dias Previstos", each [Dias Trabalhados] + [Faltas] + [Dias de Atestado], Int64.Type),
    Final = Table.RenameColumns(Table.RemoveColumns(Previstos, {"HE (hh:mm)"}), {{"Name", "Arquivo de Origem"}})
in
    Final
