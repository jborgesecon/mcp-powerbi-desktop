import asyncio
from powerbi.process_detection import detect_instances
from powerbi.xmla_connection import XMLAConnection
from powerbi.model_reader import ModelReader
from powerbi.model_writer import ModelWriter

async def main():
    print("Testing active PowerBI Desktop instance discovery...")
    instances = detect_instances()
    print("Discovered instances:", instances)
    if not instances:
        print("No active instances discovered!")
        return
        
    instance = instances[0]
    port = instance["port"]
    print(f"Connecting to instance on port {port}...")
    conn = XMLAConnection(port=port)
    await conn.discover_database()
    print(f"Active database catalog: {conn.active_database}")
    
    reader = ModelReader(conn)
    summary = await reader.get_summary()
    print("\n--- Model Summary ---")
    print(summary)
    
    print("\nTesting creating/updating a measure via TOM...")
    writer = ModelWriter(conn)
    res = await writer.upsert_measure("Tabela", "TestMeasure", "1 + 1")
    print("Write result:", res)

if __name__ == "__main__":
    asyncio.run(main())
