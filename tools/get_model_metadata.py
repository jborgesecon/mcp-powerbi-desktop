import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_model_metadata",
    description="Retrieve basic tables and measures in the active semantic model. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
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
    metadata = await reader.get_summary()
    return [types.TextContent(type="text", text=str(metadata))]
