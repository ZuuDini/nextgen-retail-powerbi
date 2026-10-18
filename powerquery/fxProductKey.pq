// Function: fxProductKey
// Normalizes product IDs from all three systems to "P-00042".
//   42 (Excel number, zeros lost)  "P00042" (inventory)  "P-00042" (sales)
(id as any) as text =>
let
    Digits = Text.Select(Text.From(id), {"0".."9"})
in
    "P-" & Text.PadStart(Digits, 5, "0")
