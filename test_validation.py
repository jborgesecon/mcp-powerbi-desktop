import subprocess
import json
import time

def main():
    print("Starting MCP Server verification test...")
    
    # Spawn the native Python MCP server
    cmd = ["python3", "mcp_server.py"]
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
        print(f"\n---> SENT:\n{json.dumps(msg, indent=2)}")

    # Helper to read a message
    def read_msg(timeout=5):
        # Read a line from stdout
        # Using simple line read
        line = proc.stdout.readline().strip()
        if line:
            try:
                msg = json.loads(line)
                print(f"\n<--- RECEIVED:\n{json.dumps(msg, indent=2)}")
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
                "name": "Validator",
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

    # Step 3: Send 'tools/list'
    list_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    send_msg(list_req)
    list_res = read_msg()
    
    if not list_res:
        print("Failed to receive tools/list response.")
        proc.terminate()
        return

    # Verify tools
    try:
        tools = list_res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "list_instances",
            "select_instance",
            "get_model_metadata",
            "list_measures",
            "get_measure",
            "update_measure",
            "create_measure",
            "create_or_update_measure",
            "run_tmsl"
        ]
        
        print("\n=== Tool Discovery Summary ===")
        all_passed = True
        for et in expected_tools:
            if et in tool_names:
                print(f"  [PASS] {et} is present")
            else:
                print(f"  [FAIL] {et} is MISSING!")
                all_passed = False
                
        if all_passed:
            print("\nVERIFICATION SUCCESSFUL: All specified tools discovered and matched the schema requirements!")
        else:
            print("\nVERIFICATION FAILED: Some expected tools are missing.")
    except Exception as e:
        print(f"Error validating tools list structure: {e}")

    # Terminate process
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()
