import asyncio
import socket

async def check_port(port):
    try:
        conn = asyncio.open_connection('127.0.0.1', port)
        reader, writer = await asyncio.wait_for(conn, timeout=0.2)
        writer.close()
        await writer.wait_closed()
        return port
    except Exception:
        return None

async def main():
    print("Scanning ports (1000-65535) on 127.0.0.1 with 0.2s timeout...")
    chunk_size = 500
    open_ports = []
    # Dynamic port range is usually where SSAS listens, let's scan 1000 to 65535
    for i in range(1000, 65536, chunk_size):
        start = i
        end = min(i + chunk_size, 65536)
        tasks = [check_port(p) for p in range(start, end)]
        results = await asyncio.gather(*tasks)
        open_ports.extend([r for r in results if r is not None])
        # Print progress occasionally
        if len(open_ports) > 0 and len(open_ports) % 5 == 0:
            print(f"Current open ports found: {open_ports}")
    
    print(f"Scan complete. Open ports: {open_ports}")

if __name__ == "__main__":
    asyncio.run(main())
