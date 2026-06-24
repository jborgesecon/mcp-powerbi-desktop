import mcp.types as types
import json
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="preview_table_data",
    description=(
        "Retrieve a small sample of rows from a specific Power BI table (similar to head()). "
        "Supports automatic instance binding if only one Power BI Desktop instance is running. "
        "Accepts an optional 'port' argument to query a specific instance directly."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Name of the table to preview. Optional if only one business-relevant table exists."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of rows to retrieve. Default is 5."
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
        limit = arguments.get("limit", 5)
        
        rows = await reader.preview_table_data(resolved_table, limit)
        if not rows:
            return [types.TextContent(type="text", text=f"Table '{resolved_table}' is empty or returned no rows.")]
            
        formatted = json.dumps(rows, indent=2, ensure_ascii=False)
        return [types.TextContent(type="text", text=formatted)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error previewing table data: {str(e)}")]
