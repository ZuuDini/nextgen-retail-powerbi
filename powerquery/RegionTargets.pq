// Query: RegionTargets  (96 rows = 4 regions x 24 months)
let
    Source = Excel.Workbook(File.Contents(DataFolder & "regional_performance.xlsx"), null, true),
    Sheet = Source{[Item = "Monthly Targets", Kind = "Sheet"]}[Data],

    // 1. Title row + blank row, then the header row.
    SkippedTitle = Table.Skip(Sheet, 2),
    Promoted = Table.PromoteHeaders(SkippedTitle, [PromoteAllScalars = true]),

    // 2. The bottom row is a Total. Keeping it would double the targets.
    RemovedTotal = Table.SelectRows(Promoted, each [Region] <> "Total"),

    // 3. Wide (one column per month) -> long (one row per region-month).
    Unpivoted = Table.UnpivotOtherColumns(RemovedTotal, {"Region"}, "Month", "TargetSales"),

    // 4. "NE" -> "Northeast";  "2024-01" -> 2024-01-01
    CleanRegion = Table.TransformColumns(Unpivoted, {{"Region", fxRegion, type text}}),
    AddedMonthStart = Table.AddColumn(CleanRegion, "MonthStart",
        each Date.FromText([Month] & "-01", [Format = "yyyy-MM-dd"]), type date),
    RemovedMonth = Table.RemoveColumns(AddedMonthStart, {"Month"}),
    Typed = Table.TransformColumnTypes(RemovedMonth, {{"TargetSales", type number}})
in
    Typed
