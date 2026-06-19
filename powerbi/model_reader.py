from powerbi.xmla_connection import XMLAConnection

def _get_val(row: dict, key: str, default: str = "") -> str:
    """Helper to retrieve dictionary values case-insensitively."""
    kl = key.lower()
    for k, v in row.items():
        if k.lower() == kl:
            return v if v is not None else default
    return default

class ModelReader:
    def __init__(self, connection: XMLAConnection):
        self.connection = connection

    async def get_summary(self) -> dict:
        """Retrieves a token-efficient summary of the semantic model's tables and measures."""
        # Query DIMENSION_TYPE = 3 (dimensions/tables) since DIMENSION_IS_SHARED is not present in all Power BI environments
        tables_query = "SELECT [Dimension_Unique_Name] FROM $SYSTEM.MDSCHEMA_DIMENSIONS WHERE [Dimension_Type] = 3"
        tables_result = await self.connection.execute_xmla(tables_query)
        
        measures_query = "SELECT [MEASURE_NAME], [MEASUREGROUP_NAME] FROM $SYSTEM.MDSCHEMA_MEASURES"
        measures_result = await self.connection.execute_xmla(measures_query)

        # Extract rows using XMLAConnection parser helper
        table_rows = self.connection._extract_rows(tables_result)
        measure_rows = self.connection._extract_rows(measures_result)
        
        table_names = []
        for row in table_rows:
            unique_name = _get_val(row, "Dimension_Unique_Name")
            name = unique_name.strip("[]")
            # Filter out internal date tables
            if name and name not in table_names and not name.startswith("LocalDateTable_") and not name.startswith("DateTableTemplate_"):
                table_names.append(name)
                
        table_measures = {name: [] for name in table_names}
        for row in measure_rows:
            measure_name = _get_val(row, "MEASURE_NAME")
            group_name = _get_val(row, "MEASUREGROUP_NAME")
            group_name_clean = group_name.strip("[]")
            if group_name_clean in table_measures:
                table_measures[group_name_clean].append(measure_name)
                
        tables_structured = []
        for name in table_names:
            tables_structured.append({
                "name": name,
                "measures": table_measures[name]
            })
            
        return {"tables": tables_structured}

    async def get_measure_dax(self, name: str) -> str:
        """Retrieves the DAX expression for a specific measure name."""
        safe_name = name.replace("'", "''")
        query = f"SELECT [EXPRESSION] FROM $SYSTEM.MDSCHEMA_MEASURES WHERE [MEASURE_NAME] = '{safe_name}'"
        result = await self.connection.execute_xmla(query)
        rows = self.connection._extract_rows(result)
        if rows:
            return _get_val(rows[0], "EXPRESSION")
        return ""

    async def list_all_measures(self) -> list[dict]:
        """Returns all measure names, expressions, and parent tables."""
        query = "SELECT [MEASURE_NAME], [MEASUREGROUP_NAME], [EXPRESSION] FROM $SYSTEM.MDSCHEMA_MEASURES"
        result = await self.connection.execute_xmla(query)
        rows = self.connection._extract_rows(result)
        measures = []
        for row in rows:
            measures.append({
                "name": _get_val(row, "MEASURE_NAME"),
                "table": _get_val(row, "MEASUREGROUP_NAME").strip("[]"),
                "expression": _get_val(row, "EXPRESSION")
            })
        return measures
