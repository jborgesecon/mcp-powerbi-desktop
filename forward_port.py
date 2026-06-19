import asyncio

async def handle_client(client_reader, client_writer):
    try:
        remote_reader, remote_writer = await asyncio.open_connection('127.0.0.1', 54048)
    except Exception as e:
        client_writer.close()
        return

    async def pipe(reader, writer):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    asyncio.create_task(pipe(client_reader, remote_writer))
    asyncio.create_task(pipe(remote_reader, client_writer))

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 54049)
    print("Proxying from 0.0.0.0:54049 to 127.0.0.1:54048...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
