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
    run_tmsl,
    list_table_columns,
    preview_table_data,
    inspect_table,
    get_calculated_columns,
    get_relationships
)

# Session State
current_connection: XMLAConnection = None

server = Server("power-bi-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    # Expose both individual tools and unified tool for complete compatibility
    create_or_update_schema = types.Tool(
        name="create_or_update_measure",
        description="Create or update a measure with a DAX expression in a table. Supports automatic instance binding if only one Power BI Desktop instance is running. Accepts an optional 'port' argument to query a specific instance directly. If multiple instances are running and no port is provided, a prior call to select_instance(port) or providing the 'port' argument is required.",
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
    return [
        list_instances.SCHEMA,
        select_instance.SCHEMA,
        get_model_metadata.SCHEMA,
        list_measures.SCHEMA,
        get_measure.SCHEMA,
        update_measure.SCHEMA,
        create_measure.SCHEMA,
        create_or_update_schema,
        run_tmsl.SCHEMA,
        list_table_columns.SCHEMA,
        preview_table_data.SCHEMA,
        inspect_table.SCHEMA,
        get_calculated_columns.SCHEMA,
        get_relationships.SCHEMA
    ]

async def resolve_connection(port: int | None = None) -> XMLAConnection:
    """
    Resolves the connection to the Power BI Desktop SSAS instance:
    1. If an explicit port argument is provided, connect to it and update current_connection.
    2. If a connection is already established, reuse it.
    3. If no connection exists, run auto-discovery:
       - If exactly one instance is running, connect and cache it.
       - If multiple instances are running, raise a disambiguation error.
       - If zero instances are running, raise a clear error.
    """
    global current_connection
    if port is not None:
        if current_connection and current_connection.port == port:
            return current_connection
        conn = XMLAConnection(port=port)
        await conn.discover_database()
        current_connection = conn
        return conn

    if current_connection is not None:
        return current_connection

    instances = detect_instances()
    if not instances:
        raise ValueError("No running Power BI Desktop instances were found.")
    elif len(instances) == 1:
        resolved_port = instances[0]["port"]
        conn = XMLAConnection(port=resolved_port)
        await conn.discover_database()
        current_connection = conn
        return conn
    else:
        raise ValueError(
            "Multiple Power BI Desktop instances are running. Please call select_instance(port) explicitly or provide a port argument."
        )

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

        # Operational tools: resolve connection either via optional port or auto-binding
        port = arguments.get("port")
        try:
            connection = await resolve_connection(port)
        except ValueError as ve:
            return [types.TextContent(type="text", text=f"Error: {str(ve)}")]

        if name == "get_model_metadata":
            return await get_model_metadata.execute(arguments, connection)

        elif name == "list_measures":
            return await list_measures.execute(arguments, connection)

        elif name == "get_measure":
            return await get_measure.execute(arguments, connection)

        elif name == "update_measure":
            return await update_measure.execute(arguments, connection)

        elif name == "create_measure":
            return await create_measure.execute(arguments, connection)

        elif name == "create_or_update_measure":
            # Delegate to create_measure handler since it handles createOrReplace upsert
            return await create_measure.execute(arguments, connection)

        elif name == "run_tmsl":
            return await run_tmsl.execute(arguments, connection)

        elif name == "list_table_columns":
            return await list_table_columns.execute(arguments, connection)

        elif name == "preview_table_data":
            return await preview_table_data.execute(arguments, connection)

        elif name == "inspect_table":
            return await inspect_table.execute(arguments, connection)

        elif name == "get_calculated_columns":
            return await get_calculated_columns.execute(arguments, connection)

        elif name == "get_relationships":
            return await get_relationships.execute(arguments, connection)

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
