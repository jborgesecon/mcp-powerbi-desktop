import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="list_table_columns",
    description=(
        "List all columns in a specific Power BI table, including their name, data type, "
        "kind (physical/calculated), hidden status, source physical column, description, and DAX expression for calculated columns. "
        "Supports automatic instance binding if only one Power BI Desktop instance is running. "
        "Accepts an optional 'port' argument to query a specific instance directly."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Name of the table to list columns for. Optional if only one business-relevant table exists."
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
        
        # Format the output clearly for the LLM
        output_lines = [f"Table: {resolved_table}", "=" * (len(resolved_table) + 7), ""]
        for col in columns:
            output_lines.append(f"Column: {col['name']}")
            output_lines.append(f"  Type: {col['data_type']}")
            output_lines.append(f"  Kind: {col['kind']}")
            output_lines.append(f"  Hidden: {col['is_hidden']}")
            if col['source']:
                output_lines.append(f"  Source Column: {col['source']}")
            if col['dax_expression']:
                output_lines.append(f"  DAX Expression:\n{col['dax_expression']}")
            if col['description']:
                output_lines.append(f"  Description: {col['description']}")
            output_lines.append("")
            
        return [types.TextContent(type="text", text="\n".join(output_lines))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error listing table columns: {str(e)}")]
