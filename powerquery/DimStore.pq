// Query: DimStore  (20 rows)
let
    Source = Excel.Workbook(File.Contents(DataFolder & "regional_performance.xlsx"), null, true),
    Sheet = Source{[Item = "Stores", Kind = "Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    Renamed = Table.RenameColumns(Promoted, {
        {"Store Code", "StoreCode"}, {"Store Name", "StoreName"}}),
    // 11 spellings of 4 regions -> 4 regions
    Cleaned = Table.TransformColumns(Renamed, {
        {"StoreCode", fxStoreKey, type text},
        {"Region", fxRegion, type text}}),
    Typed = Table.TransformColumnTypes(Cleaned, {
        {"StoreName", type text}, {"City", type text}, {"State", type text}})
in
    Typed
