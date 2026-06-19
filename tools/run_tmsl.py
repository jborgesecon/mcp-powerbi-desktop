import mcp.types as types
from powerbi.tmsl_executor import TMSLExecutor

SCHEMA = types.Tool(
    name="run_tmsl",
    description="Execute a raw TMSL script against the active model.",
    inputSchema={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Raw TMSL script JSON"}
        },
        "required": ["script"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    executor = TMSLExecutor(connection)
    result = await executor.run_script(arguments["script"])
    return [types.TextContent(type="text", text=str(result))]
