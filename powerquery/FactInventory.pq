// Query: FactInventory  (month-end on-hand units per store x product)
let
    Source = Csv.Document(File.Contents(DataFolder & "inventory_snapshots.csv"),
        [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // 1. Blank counts mean "not counted", not zero. Drop them (rule in the DQ log).
    RemovedBlank = Table.SelectRows(Promoted, each [on_hand] <> ""),

    // 2. "2024-01" -> 2024-01-31 (snapshots are month-end).
    AddedSnapshotDate = Table.AddColumn(RemovedBlank, "SnapshotDate",
        each Date.EndOfMonth(Date.FromText([month] & "-01", [Format = "yyyy-MM-dd"])), type date),

    // 3. The warehouse system writes "st001" and "P00042".
    CleanKeys = Table.TransformColumns(AddedSnapshotDate, {
        {"store", fxStoreKey, type text}, {"sku", fxProductKey, type text}}),
    Renamed = Table.RenameColumns(CleanKeys, {
        {"store", "StoreCode"}, {"sku", "ProductKey"}, {"on_hand", "OnHandUnits"}}),
    Selected = Table.SelectColumns(Renamed, {"SnapshotDate", "StoreCode", "ProductKey", "OnHandUnits"}),
    Typed = Table.TransformColumnTypes(Selected, {{"OnHandUnits", Int64.Type}}),

    // 4. ST-099 is a closed warehouse that isn't in the store master.
    //    Inner join to DimStore drops those orphan rows (counted in InventoryOrphanCheck).
    Joined = Table.NestedJoin(Typed, {"StoreCode"}, DimStore, {"StoreCode"}, "Store", JoinKind.Inner),
    RemovedJoin = Table.RemoveColumns(Joined, {"Store"})
in
    RemovedJoin
