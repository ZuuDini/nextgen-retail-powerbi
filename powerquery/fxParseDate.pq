// Function: fxParseDate
// The POS exports use three date formats:
//   2024 file:            03/05/2024   (MM/dd/yyyy, US)
//   2025 file, Jan-Jun:   2025-03-05   (ISO)
//   2025 file, Jul-Dec:   05-Jul-2025  (after the POS migration)
// Try each format in turn. Blank -> null (return lines have no ship date).
(t as nullable text) as nullable date =>
let
    S = if t = null then "" else Text.Trim(t)
in
    if S = "" then null
    else try Date.FromText(S, [Format = "MM/dd/yyyy", Culture = "en-US"])
    otherwise try Date.FromText(S, [Format = "yyyy-MM-dd", Culture = "en-US"])
    otherwise Date.FromText(S, [Format = "dd-MMM-yyyy", Culture = "en-US"])
