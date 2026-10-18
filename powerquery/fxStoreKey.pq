// Function: fxStoreKey
// Normalizes any store code style to the store master's "ST-001".
//   "ST-001"  " ST-001 "  "st001"  -> "ST-001"
// Keeps only the digits, so stray whitespace and case don't matter.
(code as any) as text =>
let
    Digits = Text.Select(Text.From(code), {"0".."9"})
in
    "ST-" & Text.PadStart(Digits, 3, "0")
