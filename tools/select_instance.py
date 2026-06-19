import mcp.types as types

SCHEMA = types.Tool(
    name="select_instance",
    description="Select an active Power BI instance port to communicate with.",
    inputSchema={
        "type": "object",
        "properties": {
            "port": {"type": "integer", "description": "The local port of the SSAS instance."}
        },
        "required": ["port"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    port = arguments["port"]
    return [types.TextContent(type="text", text=f"Successfully connected to port {port}")]
