import mcp.types as types
from powerbi.model_writer import ModelWriter

SCHEMA = types.Tool(
    name="create_measure",
    description="Creates a new measure with a DAX expression in a table. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
    inputSchema={
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Target table"},
            "name": {"type": "string", "description": "Measure name"},
            "dax": {"type": "string", "description": "DAX formula"},
            "port": {
                "type": "integer",
                "description": "Optional port of a specific running Power BI Desktop instance to query."
            }
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
