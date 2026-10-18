// Query: DimProduct  (240 rows)
let
    Source = Excel.Workbook(File.Contents(DataFolder & "product_master.xlsx"), null, true),
    Sheet = Source{[Item = "Products", Kind = "Sheet"]}[Data],

    // 1. Rows 1-3 are a title, a note and a blank row. The header is row 4.
    SkippedTitle = Table.Skip(Sheet, 3),
    Promoted = Table.PromoteHeaders(SkippedTitle, [PromoteAllScalars = true]),

    // 2. Category was a merged cell, so only the first row of each block has it.
    FilledDown = Table.FillDown(Promoted, {"Category"}),

    // 3. Rename, rebuild the key Excel stripped of its zeros, trim padded names.
    Renamed = Table.RenameColumns(FilledDown, {
        {"Product ID", "ProductKey"}, {"Product Name", "ProductName"},
        {"Unit Cost", "UnitCost"}, {"List Price", "ListPrice"}}),
    CleanText = Table.TransformColumns(Renamed, {
        {"ProductKey", fxProductKey, type text},
        {"ProductName", Text.Trim, type text}}),
    Typed = Table.TransformColumnTypes(CleanText, {
        {"Category", type text}, {"Subcategory", type text}, {"Brand", type text},
        {"UnitCost", type number}, {"ListPrice", type number}})
in
    Typed
