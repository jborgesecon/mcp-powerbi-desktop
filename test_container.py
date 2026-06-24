import subprocess
import json
import time
import sys
import os

def main():
    print("Starting MCP Container validation test...")
    
    from powerbi.process_detection import detect_instances
    instances = detect_instances()
    env_port_arg = []
    if instances:
        port = instances[0]["port"]
        print(f"Detected running Power BI instance on port {port} on host. Passing to container...")
        env_port_arg = ["-e", f"POWERBI_PORT={port}"]

    # Run the containerized MCP server.
    # We pass the host interop environment variables and mount the relevant directories.
    cmd = [
        "podman", "run", "--rm", "-i",
        "--network=host",
        "--pid=host",
        "-v", "/init:/init:ro",
        "-v", "/mnt/c:/mnt/c",
        "-v", "/run/WSL:/run/WSL",
        "-e", f"WSL_INTEROP={os.environ.get('WSL_INTEROP', '')}",
        "-e", "PATH=/mnt/c/Windows/System32/WindowsPowerShell/v1.0:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    ] + env_port_arg + [
        "localhost/power-bi-mcp:latest"
    ]
    
    print(f"Spawning container: {' '.join(cmd)}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"FAILED to spawn podman container: {e}")
        return

    # Helper to send a message
    def send_msg(msg):
        payload = json.dumps(msg) + "\n"
        proc.stdin.write(payload)
        proc.stdin.flush()
        print(f"\n---> SENT JSON-RPC:\n{json.dumps(msg, indent=2)}")

    # Helper to read a message
    def read_msg():
        line = proc.stdout.readline().strip()
        if line:
            try:
                msg = json.loads(line)
                print(f"\n<--- RECEIVED JSON-RPC:\n{json.dumps(msg, indent=2)}")
                return msg
            except Exception as e:
                print(f"Error parsing JSON from line: {line}. Error: {e}")
        return None

    # Step 1: Send 'initialize'
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "ContainerValidator",
                "version": "1.0.0"
            }
        }
    }
    
    send_msg(init_req)
    init_res = read_msg()
    if not init_res or "error" in init_res:
        print("Initialization failed or error returned.")
        proc.terminate()
        return

    # Step 2: Send 'notifications/initialized'
    initialized_ntf = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    send_msg(initialized_ntf)

    # Step 3: Call get_relationships tool without parameters
    call_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_relationships",
            "arguments": {}
        }
    }
    send_msg(call_req)
    
    # Read the response
    call_res = read_msg()
    if not call_res:
        print("No response received for tools/call.")
    elif "error" in call_res:
        print(f"Error returned from tool call: {call_res['error']}")
    else:
        print("\n=== SUCCESS ===")
        print("Relationships retrieved successfully from containerized MCP server!")
        
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()
