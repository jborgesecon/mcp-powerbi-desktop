import asyncio
import mcp_server

async def main():
    print("Running live MCP integration test...")
    print("Testing auto-binding connection and retrieving model metadata...")
    
    # Reset connection state
    mcp_server.current_connection = None
    
    # 1. Call get_model_metadata directly (should auto-discover and succeed since exactly 1 instance is running)
    res = await mcp_server.handle_call_tool("get_model_metadata", {})
    print("Metadata Response text:")
    for content in res:
        print(content.text[:200] + "..." if len(content.text) > 200 else content.text)
        
    # Verify current_connection is set
    print("\nCurrent Connection Port:", mcp_server.current_connection.port if mcp_server.current_connection else "None")
    
    print("\n--- Testing list_table_columns ('dim_colab') ---")
    res_cols = await mcp_server.handle_call_tool("list_table_columns", {"table": "dim_colab"})
    for content in res_cols:
        print(content.text[:500] + "...\n[TRUNCATED]" if len(content.text) > 500 else content.text)

    print("\n--- Testing preview_table_data ('dim_colab', limit=2) ---")
    res_preview = await mcp_server.handle_call_tool("preview_table_data", {"table": "dim_colab", "limit": 2})
    for content in res_preview:
        print(content.text[:500] + "...\n[TRUNCATED]" if len(content.text) > 500 else content.text)

    print("\n--- Testing get_calculated_columns ('dim_colab') ---")
    res_calc = await mcp_server.handle_call_tool("get_calculated_columns", {"table": "dim_colab"})
    for content in res_calc:
        print(content.text[:500] + "...\n[TRUNCATED]" if len(content.text) > 500 else content.text)

    print("\n--- Testing inspect_table ('dim_colab', limit=2) ---")
    res_inspect = await mcp_server.handle_call_tool("inspect_table", {"table": "dim_colab", "limit": 2})
    for content in res_inspect:
        print(content.text[:1000] + "...\n[TRUNCATED]" if len(content.text) > 1000 else content.text)

    print("\n--- Testing table auto-selection failure (omitting 'table' when multiple exist) ---")
    res_auto_err = await mcp_server.handle_call_tool("inspect_table", {})
    for content in res_auto_err:
        print(content.text[:400] + "..." if len(content.text) > 400 else content.text)

    print("\n--- Testing get_relationships (all relationships) ---")
    res_all_rels = await mcp_server.handle_call_tool("get_relationships", {})
    for content in res_all_rels:
        print(content.text[:1000] + "...\n[TRUNCATED]" if len(content.text) > 1000 else content.text)

    print("\n--- Testing get_relationships ('dim_colab') ---")
    res_table_rels = await mcp_server.handle_call_tool("get_relationships", {"table": "dim_colab"})
    for content in res_table_rels:
        print(content.text[:1000] + "...\n[TRUNCATED]" if len(content.text) > 1000 else content.text)

if __name__ == "__main__":
    asyncio.run(main())
