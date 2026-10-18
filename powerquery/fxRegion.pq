// Function: fxRegion
// Maps every spelling the client uses to one of four region names.
//   "NE", " north east", "Mid-West", "MW", "SOUTH", "South ", "west" ...
// An unknown spelling raises an error on purpose: you want to see it in
// the error count, not have it silently become a fifth region.
(raw as any) as text =>
let
    Key = Text.Upper(Text.Remove(Text.Trim(Text.From(raw)), {" ", "-"})),
    Map = [
        NORTHEAST = "Northeast", NE = "Northeast",
        SOUTH = "South",
        MIDWEST = "Midwest", MW = "Midwest",
        WEST = "West"
    ]
in
    if Record.HasFields(Map, Key) then Record.Field(Map, Key)
    else error Error.Record("Unknown region", "No mapping for: " & Text.From(raw))
