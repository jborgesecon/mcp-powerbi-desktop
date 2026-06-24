import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="list_measures",
    description="Returns all measure names, expressions, and parent tables. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
    inputSchema={
        "type": "object",
        "properties": {
            "port": {
                "type": "integer",
                "description": "Optional port of a specific running Power BI Desktop instance to query."
            }
        }
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    measures = await reader.list_all_measures()
    return [types.TextContent(type="text", text=str(measures))]
