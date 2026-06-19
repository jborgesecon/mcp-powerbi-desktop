import asyncio
import sys
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import Server, NotificationOptions
import mcp.types as types
from mcp.server.stdio import stdio_server

from powerbi.process_detection import detect_instances
from powerbi.xmla_connection import XMLAConnection

from tools import (
    list_instances,
    select_instance,
    get_model_metadata,
    list_measures,
    get_measure,
    update_measure,
    create_measure,
    run_tmsl
)

# Session State
current_connection: XMLAConnection = None

server = Server("power-bi-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    # Expose both individual tools and unified tool for complete compatibility
    create_or_update_schema = types.Tool(
        name="create_or_update_measure",
        description="Create or update a measure with a DAX expression in a table.",
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
    return [
        list_instances.SCHEMA,
        select_instance.SCHEMA,
        get_model_metadata.SCHEMA,
        list_measures.SCHEMA,
        get_measure.SCHEMA,
        update_measure.SCHEMA,
        create_measure.SCHEMA,
        create_or_update_schema,
        run_tmsl.SCHEMA
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    global current_connection
    arguments = arguments or {}

    try:
        if name == "list_instances":
            instances = detect_instances()
            # Auto-select if exactly one instance exists and none is currently selected
            if len(instances) == 1 and current_connection is None:
                current_connection = XMLAConnection(port=instances[0]["port"])
                await current_connection.discover_database()
            res = await list_instances.execute(arguments, current_connection)
            return res

        elif name == "select_instance":
            port = arguments["port"]
            current_connection = XMLAConnection(port=port)
            await current_connection.discover_database()
            res = await select_instance.execute(arguments, current_connection)
            return res

        # Ensure a connection is active for remaining tools
        if not current_connection:
            return [types.TextContent(type="text", text="Error: No active connection. Call 'list_instances' and 'select_instance' first.")]

        if name == "get_model_metadata":
            return await get_model_metadata.execute(arguments, current_connection)

        elif name == "list_measures":
            return await list_measures.execute(arguments, current_connection)

        elif name == "get_measure":
            return await get_measure.execute(arguments, current_connection)

        elif name == "update_measure":
            return await update_measure.execute(arguments, current_connection)

        elif name == "create_measure":
            return await create_measure.execute(arguments, current_connection)

        elif name == "create_or_update_measure":
            # Delegate to create_measure handler since it handles createOrReplace upsert
            return await create_measure.execute(arguments, current_connection)

        elif name == "run_tmsl":
            return await run_tmsl.execute(arguments, current_connection)

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing tool: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="power-bi-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
