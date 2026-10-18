// Query: FactSales  (one row per order line; returns are negative-quantity lines)
// Expected rows after cleanup: see data/expected/kpis.json -> "Row Counts".
let
    // 1. Combine both yearly exports from the folder. Everything stays TEXT
    //    until it's cleaned, so a type guess on one file can't break the other.
    Source = Folder.Files(DataFolder),
    SalesFiles = Table.SelectRows(Source, each
        Text.StartsWith([Name], "sales_transactions_") and [Extension] = ".csv"),
    Parsed = Table.AddColumn(SalesFiles, "Data", each Table.PromoteHeaders(
        Csv.Document([Content], [Delimiter = ",", Columns = 11, Encoding = 65001,
                                 QuoteStyle = QuoteStyle.Csv]),
        [PromoteAllScalars = true])),
    KeepData = Table.SelectColumns(Parsed, {"Name", "Data"}),
    Combined = Table.ExpandTableColumn(KeepData, "Data",
        {"OrderID", "LineNo", "OrderDate", "ShipDate", "StoreCode", "ProductID",
         "CustomerID", "Channel", "Quantity", "UnitPrice", "DiscountPct"}),

    // 2. The 2024 file ends with a TOTAL row. It is not a transaction.
    RemovedFooter = Table.SelectRows(Combined, each [OrderID] <> "TOTAL"),

    // 3. The 2025 export re-sent some lines. Exact duplicates -> keep one.
    RemovedSourceName = Table.RemoveColumns(RemovedFooter, {"Name"}),
    RemovedDuplicates = Table.Distinct(RemovedSourceName),

    // 4. Three date formats -> one date type.
    ParsedDates = Table.TransformColumns(RemovedDuplicates, {
        {"OrderDate", fxParseDate, type date},
        {"ShipDate", fxParseDate, type nullable date}}),

    // 5. Keys: trim/normalize so they match the dimension tables.
    CleanKeys = Table.TransformColumns(ParsedDates, {
        {"StoreCode", fxStoreKey, type text},
        {"ProductID", fxProductKey, type text}}),
    RenamedKeys = Table.RenameColumns(CleanKeys, {
        {"ProductID", "ProductKey"}, {"CustomerID", "CustomerKey"}}),

    // 6. Money and percentages: "$1,234.50" -> 1234.5 ; "15%" or "0.15" -> 15
    CleanPrice = Table.TransformColumns(RenamedKeys, {{"UnitPrice",
        each Number.FromText(Text.Remove(_, {"$", ","}), "en-US"), type number}}),
    CleanDiscount = Table.TransformColumns(CleanPrice, {{"DiscountPct",
        each if Text.EndsWith(_, "%")
             then Number.FromText(Text.TrimEnd(_, "%"), "en-US")
             else Number.Round(Number.FromText(_, "en-US") * 100),
        Int64.Type}}),
    Typed = Table.TransformColumnTypes(CleanDiscount, {
        {"OrderID", type text}, {"LineNo", Int64.Type}, {"CustomerKey", type text},
        {"Channel", type text}, {"Quantity", Int64.Type}}),

    // 7. Derived columns used by the measures.
    AddedLineAmount = Table.AddColumn(Typed, "LineAmount",
        each [Quantity] * [UnitPrice] * (1 - [DiscountPct] / 100), type number),
    AddedIsReturn = Table.AddColumn(AddedLineAmount, "IsReturn",
        each [Quantity] < 0, type logical)
in
    AddedIsReturn
