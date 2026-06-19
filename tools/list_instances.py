import mcp.types as types
from powerbi.process_detection import detect_instances

SCHEMA = types.Tool(
    name="list_instances",
    description="List running Power BI Desktop instances and their local ports.",
    inputSchema={"type": "object", "properties": {}}
)

async def execute(arguments: dict, connection) -> list[types.TextContent]:
    instances = detect_instances()
    return [types.TextContent(type="text", text=str(instances))]
