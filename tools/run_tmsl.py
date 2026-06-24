import mcp.types as types
from powerbi.tmsl_executor import TMSLExecutor

SCHEMA = types.Tool(
    name="run_tmsl",
    description="Execute a raw TMSL script against the active model. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
    inputSchema={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Raw TMSL script JSON"},
            "port": {
                "type": "integer",
                "description": "Optional port of a specific running Power BI Desktop instance to query."
            }
        },
        "required": ["script"]
    }
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    executor = TMSLExecutor(connection)
    result = await executor.run_script(arguments["script"])
    return [types.TextContent(type="text", text=str(result))]
