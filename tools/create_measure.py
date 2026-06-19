import mcp.types as types
from powerbi.model_writer import ModelWriter

SCHEMA = types.Tool(
    name="create_measure",
    description="Creates a new measure with a DAX expression in a table.",
    inputSchema={
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Target table"},
            "name": {"type": "string", "description": "Measure name"},
            "dax": {"type": "string", "description": "DAX formula"}
        },
        "required": ["table", "name", "dax"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    writer = ModelWriter(connection)
    result = await writer.upsert_measure(
        table=arguments["table"],
        name=arguments["name"],
        dax=arguments["dax"]
    )
    return [types.TextContent(type="text", text=str(result))]
