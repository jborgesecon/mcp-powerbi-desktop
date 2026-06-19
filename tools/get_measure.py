import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_measure",
    description="Retrieve the DAX expression of a specific measure.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the measure"}
        },
        "required": ["name"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    dax = await reader.get_measure_dax(arguments["name"])
    return [types.TextContent(type="text", text=dax)]
