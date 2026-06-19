import asyncio
import socket

async def check_port(port):
    try:
        # Try to connect
        conn = asyncio.open_connection('127.0.0.1', port)
        reader, writer = await asyncio.wait_for(conn, timeout=0.05)
        writer.close()
        await writer.wait_closed()
        return port
    except Exception:
        return None

async def main():
    print("Scanning dynamic ports (49152-65535) on 127.0.0.1 for open ports...")
    # Scan in chunks to avoid descriptor limits
    chunk_size = 1000
    open_ports = []
    for i in range(49152, 65536, chunk_size):
        start = i
        end = min(i + chunk_size, 65536)
        tasks = [check_port(p) for p in range(start, end)]
        results = await asyncio.gather(*tasks)
        open_ports.extend([r for r in results if r is not None])
    
    print(f"Scan complete. Open ports: {open_ports}")

if __name__ == "__main__":
    asyncio.run(main())
