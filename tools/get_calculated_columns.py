import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_calculated_columns",
    description=(
        "Retrieve only the calculated columns and their DAX formulas from a specific table. "
        "Supports automatic instance binding if only one Power BI Desktop instance is running. "
        "Accepts an optional 'port' argument to query a specific instance directly."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Name of the table to retrieve calculated columns for. Optional if only one business-relevant table exists."
            },
            "port": {
                "type": "integer",
                "description": "Optional port of a specific running Power BI Desktop instance to query."
            }
        }
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    try:
        resolved_table = await reader.resolve_table_name(arguments.get("table"))
        columns = await reader.get_table_columns(resolved_table)
        
        calculated_cols = [c for c in columns if c["kind"] == "calculated"]
        
        if not calculated_cols:
            return [types.TextContent(type="text", text=f"No calculated columns found in table '{resolved_table}'.")]
            
        output_lines = [f"Calculated Columns in Table: {resolved_table}", "=" * (len(resolved_table) + 29), ""]
        for col in calculated_cols:
            desc = f" - {col['description']}" if col['description'] else ""
            hidden_str = " (Hidden)" if col['is_hidden'] else ""
            output_lines.append(f"* **{col['name']}** ({col['data_type']}){hidden_str}{desc}")
            output_lines.append("  DAX Expression:")
            output_lines.append("  ```dax")
            output_lines.append(col['dax_expression'])
            output_lines.append("  ```")
            output_lines.append("")
            
        return [types.TextContent(type="text", text="\n".join(output_lines))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error retrieving calculated columns: {str(e)}")]
