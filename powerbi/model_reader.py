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

    async def get_valid_tables(self) -> list[str]:
        """Returns a list of non-technical tables in the model."""
        tables_res = await self.connection.execute_xmla("SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES")
        tables = self.connection._extract_rows(tables_res)
        valid_tables = []
        for t in tables:
            name = t.get("Name")
            if not name:
                continue
            if name.startswith("LocalDateTable_") or name.startswith("DateTableTemplate_"):
                continue
            if "DateTableTemplate" in name or "LocalDateTable" in name:
                continue
            if name.startswith("__"):
                continue
            valid_tables.append(name)
        return valid_tables

    async def resolve_table_name(self, table_name: str | None) -> str:
        """
        Resolves the table name, verifying existence and/or auto-selecting.
        Raises ValueError if cannot resolve uniquely.
        """
        tables_res = await self.connection.execute_xmla("SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES")
        all_tables = self.connection._extract_rows(tables_res)
        all_table_names = [t.get("Name") for t in all_tables if t.get("Name")]

        valid_tables = []
        for name in all_table_names:
            if name.startswith("LocalDateTable_") or name.startswith("DateTableTemplate_"):
                continue
            if "DateTableTemplate" in name or "LocalDateTable" in name:
                continue
            if name.startswith("__"):
                continue
            valid_tables.append(name)

        if table_name:
            clean_name = table_name.strip("'").strip('"')
            for vt in valid_tables:
                if vt.lower() == clean_name.lower():
                    return vt
            for t in all_table_names:
                if t.lower() == clean_name.lower():
                    return t
            raise ValueError(f"Table '{table_name}' was not found in the model.")

        if not valid_tables:
            raise ValueError("No tables found in the model.")
        elif len(valid_tables) == 1:
            return valid_tables[0]
        else:
            tables_list = ", ".join(f"'{name}'" for name in sorted(valid_tables))
            raise ValueError(
                f"Multiple tables exist. Please specify a table name. Available tables: {tables_list}"
            )

    async def get_table_columns(self, table_name: str) -> list[dict]:
        """Returns detailed column metadata for a specified table."""
        tables_res = await self.connection.execute_xmla("SELECT [ID], [Name] FROM $SYSTEM.TMSCHEMA_TABLES")
        tables = self.connection._extract_rows(tables_res)
        table_id = None
        for t in tables:
            if t.get("Name") and t.get("Name").lower() == table_name.lower():
                table_id = t.get("ID")
                break
        
        if table_id is None:
            raise ValueError(f"Table '{table_name}' was not found in the model.")

        columns_res = await self.connection.execute_xmla(
            f"SELECT * FROM $SYSTEM.TMSCHEMA_COLUMNS WHERE [TableID] = {table_id}"
        )
        columns = self.connection._extract_rows(columns_res)

        processed = []
        for col in columns:
            name = col.get("ExplicitName") or col.get("InferredName")
            if not name:
                continue
            
            type_val = col.get("Type")
            if type_val == 1:
                kind = "physical"
            elif type_val == 2:
                kind = "calculated"
            elif type_val == 3:
                if name.startswith("RowNumber-"):
                    continue
                kind = "system"
            else:
                kind = f"unknown ({type_val})"

            dt_code = col.get("ExplicitDataType")
            if dt_code == 1 and col.get("InferredDataType"):
                dt_code = col.get("InferredDataType")
            
            dt_mapping = {
                1: "Variant",
                2: "String",
                6: "Numeric",
                9: "DateTime",
                10: "Boolean",
                11: "Binary"
            }
            data_type = dt_mapping.get(dt_code, f"Unknown ({dt_code})")

            processed.append({
                "name": name,
                "data_type": data_type,
                "kind": kind,
                "is_hidden": col.get("IsHidden") == True,
                "source": col.get("SourceColumn") or "",
                "dax_expression": col.get("Expression") or "",
                "description": col.get("Description") or ""
            })
        return processed

    async def preview_table_data(self, table_name: str, limit: int = 5) -> list[dict]:
        """Returns a small sample of rows from a specified table."""
        clean_name = table_name.strip("'").strip('"')
        safe_name = clean_name.replace("'", "''")
        dax_query = f"EVALUATE TOPN({limit}, '{safe_name}')"
        res = await self.connection.execute_xmla(dax_query)
        rows = self.connection._extract_rows(res)
        
        cleaned_rows = []
        for r in rows:
            cleaned_row = {}
            for k, v in r.items():
                if "[" in k and k.endswith("]"):
                    col_name = k.split("[", 1)[1][:-1]
                    cleaned_row[col_name] = v
                else:
                    cleaned_row[k] = v
            cleaned_rows.append(cleaned_row)
        return cleaned_rows

    async def get_relationships(self, table_name: str | None = None) -> list[dict]:
        """
        Retrieves relationships in the model.
        If table_name is specified, returns only relationships involving that table.
        By default, filters out technical/system tables (like LocalDateTable, DateTableTemplate, __).
        """
        tables_res = await self.connection.execute_xmla("SELECT [ID], [Name] FROM $SYSTEM.TMSCHEMA_TABLES")
        tables_rows = self.connection._extract_rows(tables_res)
        table_id_to_name = {}
        for r in tables_rows:
            if r.get("ID") is not None and r.get("Name") is not None:
                table_id_to_name[int(r["ID"])] = r["Name"]

        columns_res = await self.connection.execute_xmla("SELECT [ID], [TableID], [ExplicitName], [InferredName] FROM $SYSTEM.TMSCHEMA_COLUMNS")
        columns_rows = self.connection._extract_rows(columns_res)
        column_id_to_name = {}
        for r in columns_rows:
            if r.get("ID") is not None:
                name = r.get("ExplicitName") or r.get("InferredName")
                column_id_to_name[int(r["ID"])] = name

        rel_res = await self.connection.execute_xmla("SELECT * FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS")
        rel_rows = self.connection._extract_rows(rel_res)

        def is_system_table(name):
            if not name:
                return True
            if name.startswith("LocalDateTable_") or name.startswith("DateTableTemplate_"):
                return True
            if "DateTableTemplate" in name or "LocalDateTable" in name:
                return True
            if name.startswith("__"):
                return True
            return False

        def get_cardinality_str(card):
            if card == 1:
                return "1"
            elif card == 2:
                return "many"
            return "unknown"

        def get_direction_str(direction):
            if direction == 1:
                return "Single"
            elif direction == 2:
                return "Both"
            elif direction == 3:
                return "Automatic"
            return f"Unknown ({direction})"

        resolved_table = None
        if table_name:
            resolved_table = await self.resolve_table_name(table_name)

        mapped_rels = []
        for r in rel_rows:
            from_table_id = int(r.get("FromTableID")) if r.get("FromTableID") is not None else None
            to_table_id = int(r.get("ToTableID")) if r.get("ToTableID") is not None else None
            from_column_id = int(r.get("FromColumnID")) if r.get("FromColumnID") is not None else None
            to_column_id = int(r.get("ToColumnID")) if r.get("ToColumnID") is not None else None

            from_table = table_id_to_name.get(from_table_id, f"Table_{from_table_id}")
            to_table = table_id_to_name.get(to_table_id, f"Table_{to_table_id}")

            if not resolved_table or not is_system_table(resolved_table):
                if is_system_table(from_table) or is_system_table(to_table):
                    continue

            if resolved_table:
                if from_table.lower() != resolved_table.lower() and to_table.lower() != resolved_table.lower():
                    continue

            from_column = column_id_to_name.get(from_column_id, f"Column_{from_column_id}")
            to_column = column_id_to_name.get(to_column_id, f"Column_{to_column_id}")

            from_card = get_cardinality_str(r.get("FromCardinality"))
            to_card = get_cardinality_str(r.get("ToCardinality"))

            rel_type = f"{from_card} to {to_card}"
            direction = get_direction_str(r.get("CrossFilteringBehavior"))
            is_active = r.get("IsActive") != False

            mapped_rels.append({
                "from_table": from_table,
                "from_column": from_column,
                "to_table": to_table,
                "to_column": to_column,
                "type": rel_type,
                "direction": direction,
                "is_active": is_active
            })

        return mapped_rels


