// Query: DimRegion  (4 rows)
// Shared by DimStore and RegionTargets. Targets are set per region, not per
// store, so a region table gives both of them a common one-side to filter from.
let
    Source = DimStore,
    Regions = Table.Distinct(Table.SelectColumns(Source, {"Region"})),
    Sorted = Table.Sort(Regions, {{"Region", Order.Ascending}})
in
    Sorted
