import subprocess
import json
import time
import sys

def main():
    print("Connecting to containerized Power BI MCP server (with --pid=host --network=host)...")
    
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

    # Helper to read a message
    def read_msg():
        line = proc.stdout.readline().strip()
        if line:
            try:
                return json.loads(line)
            except Exception as e:
                pass
        return None

    # Step 1: Send 'initialize'
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "QueryTool", "version": "1.0.0"}
        }
    }
    
    send_msg(init_req)
    init_res = read_msg()
    if not init_res or "error" in init_res:
        print("Initialization failed.")
        proc.terminate()
        return

    # Send 'notifications/initialized'
    send_msg({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })

    # Step 2: Call 'list_instances'
    print("Calling list_instances...")
    send_msg({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_instances",
            "arguments": {}
        }
    })
    
    list_res = read_msg()
    if not list_res or "error" in list_res:
        print(f"Failed to list instances: {list_res}")
        proc.terminate()
        return

    text_content = list_res["result"]["content"][0]["text"]
    # Convert string representation of list of dicts to python object
    # text_content is like "[{'pid': 123, 'port': 456, 'name': '...'}]" or "[]"
    try:
        # Evaluate string safely
        import ast
        instances = ast.literal_eval(text_content)
    except Exception as e:
        print(f"Error parsing instances text content: {e}. Raw content: {text_content}")
        proc.terminate()
        return

    print(f"Detected running instances: {instances}")
    if not instances:
        print("No running Power BI instances found.")
        proc.terminate()
        return

    # Step 3: Select the instance (if more than one, pick first, but auto-select should have kicked in)
    # Let's call select_instance just to be safe
    selected_port = instances[0]["port"]
    print(f"Selecting instance on port {selected_port}...")
    send_msg({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "select_instance",
            "arguments": {"port": selected_port}
        }
    })
    
    select_res = read_msg()
    print(f"Select result: {select_res.get('result', {}).get('content', [{}])[0].get('text')}")

    # Step 4: Call get_model_metadata
    print("Calling get_model_metadata...")
    send_msg({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_model_metadata",
            "arguments": {}
        }
    })
    
    meta_res = read_msg()
    if not meta_res or "error" in meta_res:
        print(f"Failed to get metadata: {meta_res}")
        proc.terminate()
        return

    meta_text = meta_res["result"]["content"][0]["text"]
    try:
        metadata = ast.literal_eval(meta_text)
    except Exception as e:
        print(f"Error parsing metadata text content: {e}. Raw content: {meta_text}")
        proc.terminate()
        return

    print("\n--- RESULTS ---")
    tables = metadata.get("tables", [])
    print(f"Total dashboards/instances running: {len(instances)}")
    print(f"Active Instance Database Tables count: {len(tables)}")
    print("Tables list:")
    for t in tables:
        print(f"  - Table: {t['name']} (Measures count: {len(t.get('measures', []))})")

    # Step 5: Call list_measures
    print("\nCalling list_measures...")
    send_msg({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "list_measures",
            "arguments": {}
        }
    })
    
    measures_res = read_msg()
    measures = []
    if measures_res and "result" in measures_res:
        measures_text = measures_res["result"]["content"][0]["text"]
        try:
            measures = ast.literal_eval(measures_text)
        except Exception as e:
            pass

    if measures:
        print(f"Total measures found: {len(measures)}")
        # Print one measure
        one_m = measures[0]
        print(f"\nExample Measure Details:")
        print(f"  Name: {one_m.get('name')}")
        print(f"  Table: {one_m.get('table')}")
        print(f"  DAX Code:")
        print(f"----------------------------------------")
        print(one_m.get('expression'))
        print(f"----------------------------------------")
    else:
        print("No measures found in the model.")

    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()
