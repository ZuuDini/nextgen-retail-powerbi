// Query: DimCustomer  (6,500 rows)
let
    Source = Json.Document(File.Contents(DataFolder & "customers.json")),

    // 1. The file is {exported_at, customers:[...]}. Take the list and turn it into a table.
    Customers = Source[customers],
    AsTable = Table.FromList(Customers, Splitter.SplitByNothing(), {"Record"}),
    Expanded = Table.ExpandRecordColumn(AsTable, "Record",
        {"customer_id", "segment", "signup_date", "demographics", "address"}),

    // 2. Two nested records -> flat columns.
    ExpandedDemo = Table.ExpandRecordColumn(Expanded, "demographics",
        {"age", "gender", "income_band"}),
    ExpandedAddr = Table.ExpandRecordColumn(ExpandedDemo, "address",
        {"city", "state", "home_store"}),
    Renamed = Table.RenameColumns(ExpandedAddr, {
        {"customer_id", "CustomerKey"}, {"segment", "Segment"},
        {"signup_date", "SignupDate"}, {"age", "Age"}, {"gender", "Gender"},
        {"income_band", "IncomeBand"}, {"city", "City"}, {"state", "State"},
        {"home_store", "HomeStore"}}),

    // 3. Lost segments: label them, don't drop the customers (their sales are real).
    FilledSegment = Table.ReplaceValue(Renamed, null, "Unassigned",
        Replacer.ReplaceValue, {"Segment"}),

    // 4. Ages of 0, 7, 130, 999 are entry errors. Null them, keep the customer.
    CleanAge = Table.TransformColumns(FilledSegment, {{"Age",
        each if _ = null or _ < 16 or _ > 100 then null else _, Int64.Type}}),

    // 5. F / female / Female -> Female, etc.
    CleanGender = Table.TransformColumns(CleanAge, {{"Gender",
        each Record.FieldOrDefault([F = "Female", FEMALE = "Female", M = "Male",
            MALE = "Male", NB = "Non-binary", #"NON-BINARY" = "Non-binary"],
            Text.Upper(_), "Unknown"), type text}}),
    Typed = Table.TransformColumnTypes(CleanGender, {
        {"CustomerKey", type text}, {"Segment", type text}, {"SignupDate", type date},
        {"IncomeBand", type text}, {"City", type text}, {"State", type text},
        {"HomeStore", type text}}),

    // 6. Conditional column for the demographic visuals.
    AddedAgeBand = Table.AddColumn(Typed, "AgeBand", each
        if [Age] = null then "Unknown"
        else if [Age] < 25 then "18-24"
        else if [Age] < 35 then "25-34"
        else if [Age] < 45 then "35-44"
        else if [Age] < 55 then "45-54"
        else if [Age] < 65 then "55-64"
        else "65+", type text)
in
    AddedAgeBand
