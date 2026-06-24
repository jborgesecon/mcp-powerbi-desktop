import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_measure",
    description="Retrieve the DAX expression of a specific measure. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the measure"},
            "port": {
                "type": "integer",
                "description": "Optional port of a specific running Power BI Desktop instance to query."
            }
        },
        "required": ["name"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    dax = await reader.get_measure_dax(arguments["name"])
    return [types.TextContent(type="text", text=dax)]
