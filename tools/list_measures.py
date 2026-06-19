import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="list_measures",
    description="Returns all measure names, expressions, and parent tables.",
    inputSchema={"type": "object", "properties": {}}
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    measures = await reader.list_all_measures()
    return [types.TextContent(type="text", text=str(measures))]
