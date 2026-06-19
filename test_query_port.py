import asyncio
import xmltodict
import httpx
from powerbi.xmla_connection import XMLAConnection
from powerbi.model_reader import ModelReader

async def main():
    port = 54048
    print(f"Connecting to XMLA connection on port {port}...")
    conn = XMLAConnection(port=port)
    
    print("Discovering database catalog...")
    await conn.discover_database()
    print(f"Discovered active database catalog: {conn.active_database}")
    
    reader = ModelReader(conn)
    print("Fetching model summary...")
    summary = await reader.get_summary()
    print("\n--- Model Summary ---")
    print(summary)
    
    print("\nFetching all measures...")
    measures = await reader.list_all_measures()
    print("\n--- Measures ---")
    for m in measures:
        print(f"Measure: {m['name']} in Table: {m['table']}")
        print(f"DAX Expression:\n{m['expression']}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
