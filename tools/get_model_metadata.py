import mcp.types as types
from powerbi.model_reader import ModelReader

SCHEMA = types.Tool(
    name="get_model_metadata",
    description="Retrieve basic tables and measures in the active semantic model.",
    inputSchema={"type": "object", "properties": {}}
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    reader = ModelReader(connection)
    metadata = await reader.get_summary()
    return [types.TextContent(type="text", text=str(metadata))]
