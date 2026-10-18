// Query: InventoryOrphanCheck  (right-click > uncheck "Enable load")
// A data-quality query, not a model table: inventory rows whose store isn't
// in the store master. Expected: 720 rows, all "ST-099" (Jan-Mar 2025).
let
    Source = Csv.Document(File.Contents(DataFolder & "inventory_snapshots.csv"),
        [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    CleanStore = Table.TransformColumns(Promoted, {{"store", fxStoreKey, type text}}),
    Orphans = Table.NestedJoin(CleanStore, {"store"}, DimStore, {"StoreCode"}, "Store", JoinKind.LeftAnti),
    Summary = Table.Group(Orphans, {"store"}, {{"Rows", each Table.RowCount(_), Int64.Type}})
in
    Summary
