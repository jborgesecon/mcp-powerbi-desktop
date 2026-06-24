import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_relationships",
    description=(
        "Retrieve relationships in the semantic model. Can filter by a specific table name "
        "to retrieve only relationships relevant to that table (where it is either the source or the target). "
        "Returns column keys, relationship type (1 to many, many to many, etc.), direction, and active status. "
        "Supports automatic instance binding if only one Power BI Desktop instance is running. "
        "Accepts an optional 'port' argument to query a specific instance directly."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Optional name of the table to retrieve relationships for. If omitted, returns all model relationships."
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
        table_param = arguments.get("table")
        relationships = await reader.get_relationships(table_param)
        
        if not relationships:
            if table_param:
                return [types.TextContent(type="text", text=f"No relationships found involving table '{table_param}'.")]
            else:
                return [types.TextContent(type="text", text="No relationships found in the semantic model.")]
        
        if table_param:
            # We resolve it to get the correct casing for the header
            resolved_table = await reader.resolve_table_name(table_param)
            title = f"Relationships involving table: {resolved_table}"
        else:
            title = "All Semantic Model Relationships"
            
        output_lines = [title, "=" * len(title), ""]
        for rel in relationships:
            active_str = "" if rel["is_active"] else " (Inactive)"
            output_lines.append(
                f"* {rel['from_table']}[{rel['from_column']}] -> {rel['to_table']}[{rel['to_column']}] "
                f"({rel['type']}, direction: {rel['direction']}){active_str}"
            )
            
        return [types.TextContent(type="text", text="\n".join(output_lines))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error retrieving relationships: {str(e)}")]
