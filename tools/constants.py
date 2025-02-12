STRATEGY_INSERT = "INSERT"
STRATEGY_UPDATE = "UPDATE"
STRATEGY_INSERT_UPDATE = "INSERT_UPDATE"
STRATEGY_INSERT_UPDATE_DELETE = "INSERT_UPDATE_DELETE"

# List of supported import/export formats so far
XLSX = "xlsx"
CSV = "csv"
JSON = "json"
SUPPORTED_FORMATS = [XLSX, CSV, JSON]

# other types: https://stackoverflow.com/a/50860387
CONTENT_TYPES = {
    CSV: "text/csv",
    JSON: "application/json",
    XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
