// Conciliação em duas passadas:
//   1. pelo documento (título do boleto ou número do contas a pagar);
//   2. o que sobrou, por data e valor (PIX sem identificação).
// O que não casa em nenhuma passada vira pendência: "Só no extrato" ou "Só no sistema".
let
    Extrato = #"Extrato Bancário",
    Sistema = #"Títulos no Sistema",

    // Passada 1: documento
    PorDocumento = Table.ExpandTableColumn(
        Table.NestedJoin(Extrato, {"Documento"}, Sistema, {"Documento"}, "S", JoinKind.Inner),
        "S", {"Data", "Valor", "Descrição"}, {"Data no Sistema", "Valor no Sistema", "Descrição"}),
    Casados1 = Table.AddColumn(
        Table.AddColumn(PorDocumento, "Status", each
            if Number.Abs([Valor] - [Valor no Sistema]) < 0.005 then "Conciliado" else "Valor divergente", type text),
        "Regra", each "Documento", type text),

    RestoExtrato = Table.RemoveColumns(
        Table.NestedJoin(Extrato, {"Documento"}, Sistema, {"Documento"}, "x", JoinKind.LeftAnti), {"x"}),
    RestoSistema = Table.RemoveColumns(
        Table.NestedJoin(Sistema, {"Documento"}, Extrato, {"Documento"}, "x", JoinKind.LeftAnti), {"x"}),

    // Passada 2: data e valor
    PorDataValor = Table.ExpandTableColumn(
        Table.NestedJoin(RestoExtrato, {"Data", "Valor"}, RestoSistema, {"Data", "Valor"}, "S", JoinKind.Inner),
        "S", {"Documento", "Data", "Valor", "Descrição"}, {"Documento no Sistema", "Data no Sistema", "Valor no Sistema", "Descrição"}),
    Casados2 = Table.AddColumn(Table.AddColumn(
        Table.RemoveColumns(PorDataValor, {"Documento"}), "Status", each "Conciliado", type text),
        "Regra", each "Data e valor", type text),
    Casados2Doc = Table.RenameColumns(Casados2, {{"Documento no Sistema", "Documento"}}),

    SoExtrato = Table.AddColumn(Table.AddColumn(
        Table.NestedJoin(RestoExtrato, {"Data", "Valor"}, RestoSistema, {"Data", "Valor"}, "x", JoinKind.LeftAnti),
        "Status", each "Só no extrato", type text), "Regra", each "Pendente", type text),
    SoSistema = Table.RenameColumns(
        Table.AddColumn(Table.AddColumn(
            Table.NestedJoin(RestoSistema, {"Data", "Valor"}, RestoExtrato, {"Data", "Valor"}, "x", JoinKind.LeftAnti),
            "Status", each "Só no sistema", type text), "Regra", each "Pendente", type text),
        {{"Data", "Data no Sistema"}, {"Valor", "Valor no Sistema"}}),

    Colunas = {"Status", "Regra", "Data", "Data no Sistema", "Documento", "Histórico", "Descrição", "Valor", "Valor no Sistema"},
    Tudo = Table.Combine({
        Table.SelectColumns(Casados1, Colunas, MissingField.UseNull),
        Table.SelectColumns(Casados2Doc, Colunas, MissingField.UseNull),
        Table.SelectColumns(SoExtrato, Colunas, MissingField.UseNull),
        Table.SelectColumns(SoSistema, Colunas, MissingField.UseNull)}),
    Renomeado = Table.RenameColumns(Tudo, {{"Data", "Data no Extrato"}, {"Valor", "Valor no Extrato"}}),
    Diferenca = Table.AddColumn(Renomeado, "Diferença", each
        (if [Valor no Extrato] = null then 0 else [Valor no Extrato]) - (if [Valor no Sistema] = null then 0 else [Valor no Sistema]),
        type number),
    Contagem = Table.AddColumn(Diferenca, "Lançamentos", each 1, Int64.Type),
    Tipos = Table.TransformColumnTypes(Contagem, {{"Status", type text}, {"Regra", type text},
        {"Data no Extrato", type date}, {"Data no Sistema", type date}, {"Documento", type text}, {"Histórico", type text},
        {"Descrição", type text}, {"Valor no Extrato", type number}, {"Valor no Sistema", type number}}),
    Ordem = Table.Sort(Tipos, {{"Status", Order.Descending}, {"Data no Extrato", Order.Ascending}})
in
    Ordem
