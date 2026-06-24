# Power BI Desktop Companion MCP Server

A Model Context Protocol (MCP) server that acts as a local companion tool for actively running Power BI Desktop (`.pbix`) sessions. It attaches to the live in-memory Analysis Services engine on the local machine (similar to DAX Studio or Tabular Editor).

This companion tool is designed **ONLY** for local running Power BI Desktop instances. It communicates using Windows PowerShell interop to run OLE DB queries and Tabular Object Model (TOM) mutations.

---

## Architecture & Features

1. **Windows PowerShell OLE DB / TOM Bridge**: Executes native OLE DB commands (using the MSOLAP provider) and Tabular Object Model (TOM) scripts directly against the host machine's Analysis Services engine.
2. **Dynamic Host Instance Discovery**: Scans host processes to locate the dynamic ports, PIDs, database catalog GUIDs, table counts, and measure counts of all open `.pbix` files.
3. **Case-Insensitive Metadata Parsing**: Robust schema extraction from system DMVs, filtering out internal tables (`LocalDateTable_*`, `DateTableTemplate_*`) to present clean models.
4. **Live Model Mutations**: Directly creates or updates measures in the active `.pbix` session in-memory, committing changes using TOM's `SaveChanges()`.
5. **Stateful Connection Management**: Retains connection info (selected port and database catalog) in-memory across MCP requests, auto-selecting if only one instance is active.

---

## Tools Exposed

* `list_instances`: Lists active local Power BI Desktop instances and their ports.
* `select_instance(port)`: Connects the MCP server session to a specific port.
* `get_model_metadata`: Returns a token-efficient summary of tables and measures.
* `list_measures`: Returns all measure names, expressions, and parent tables.
* `get_measure(name)`: Retrieves the DAX formula for a specific measure.
* `create_measure(table, name, dax)`: Creates a new measure in a table.
* `update_measure(table, name, dax)`: Updates an existing measure's formula.
* `create_or_update_measure(table, name, dax)`: Unified tool to create or update a measure.
* `run_tmsl(script)`: Runs Tabular Model Scripting Language (TMSL) scripts.
* `get_relationships(table)`: Retrieves relationships in the semantic model with columns, types, and cross-filtering direction.

---

## 📦 Container Setup & Build with Podman

### 1. Build the Image
To build the Podman container image natively from the Dockerfile, run:
```bash
podman build -t power-bi-mcp:latest .
```

### 2. Verify the Image Exists
Confirm the image has been successfully created and registered in Podman:
```bash
podman images
```
Expected output:
```
REPOSITORY                 TAG         IMAGE ID      CREATED        SIZE
localhost/power-bi-mcp     latest      e5b030e749ee  1 minute ago   627 MB
```

---

## 🚀 Running the Container (WSL2 / Linux)

Because local Analysis Services runs on the Windows host and requires host execution interop, the container must be started with host network namespace access, a mount of the `/mnt/c` drive, and access to the WSL interop sockets.

### Ephemeral Mode (Interactive / stdio)
To run the server dynamically for standard I/O communication (e.g. connected to OpenWebUI or an agent):
```bash
podman run --rm -i \
  --network=host \
  --pid=host \
  -v /init:/init:ro \
  -v /mnt/c:/mnt/c \
  -v /run/WSL:/run/WSL \
  -e WSL_INTEROP=$WSL_INTEROP \
  -e PATH="/mnt/c/Windows/System32/WindowsPowerShell/v1.0:$PATH" \
  power-bi-mcp:latest
```

### Detached Mode (Background proxy / testing)
If running a background daemon/test container:
```bash
podman run --rm -d \
  --name power-bi-mcp-bg \
  --network=host \
  --pid=host \
  -v /init:/init:ro \
  -v /mnt/c:/mnt/c \
  -v /run/WSL:/run/WSL \
  -e WSL_INTEROP=$WSL_INTEROP \
  -e PATH="/mnt/c/Windows/System32/WindowsPowerShell/v1.0:$PATH" \
  power-bi-mcp:latest
```

### Accessing the Running Instance
If direct interactive shell access is required in the container for debugging:
```bash
podman exec -it <container_id> /bin/bash
```

---

## 🔍 Validation of MCP Functionality

You can validate the containerized MCP service programmatically using the validation script [test_container.py](file:///home/john/src/docker-setup/mcp-powerbi-desktop/power-bi/test_container.py). This script initiates the JSON-RPC stdio handshake and invokes the new relationship retrieval tool:

```bash
poetry run python test_container.py
```

### Expected Output Structure (JSON-RPC)
When the validation script queries relationships for a table (e.g., `dim_colab`), the output will resemble:
```json
---> SENT JSON-RPC:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_relationships",
    "arguments": {
      "table": "dim_colab"
    }
  }
}

<--- RECEIVED JSON-RPC:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Relationships involving table: dim_colab\n========================================\n\n* dim_colab[CC_INDEX] -> dim_novo_ccusto[MASCARA] (many to 1, direction: Single)\n* dim_colab[codcoligada] -> ajuste_vt[codcoligada] (many to 1, direction: Single)"
      }
    ],
    "isError": false
  }
}
```

---

## 🛠️ Troubleshooting

### 1. `FileNotFoundError: [Errno 2] No such file or directory: 'powershell.exe'`
* **Cause**: The kernel inside the container was unable to locate or execute `powershell.exe`.
* **Fix**: Ensure `/mnt/c` is mounted in the container at `/mnt/c`, and add `/mnt/c/Windows/System32/WindowsPowerShell/v1.0` to the container's `PATH`.

### 2. WSL `UtilBindVsockAnyPort: socket failed` or `PE binary: Invalid argument`
* **Cause**: Rootless Podman isolates the vsock driver sockets (`/dev/vsock`) and namespaces.
* **Fix**: Run the container using standard Docker Desktop (which configures WSL interop permissions natively), or run the command with `--privileged` and `/init` mounted (`-v /init:/init:ro`). Alternatively, execute the server natively on the WSL host using `poetry run python mcp_server.py`.

---

## 🔄 Updating the Image for Future Versions

Follow these guidelines to update and deploy new versions of the MCP container:

### 1. Version Tagging Strategy
Always tag your builds semantically to keep tracks of changes and avoid deploying broken setups:
* `latest`: Matches the current bleeding-edge stable build.
* `v1`, `v2`: Major versions matching major database schema support iterations.
* `vX.Y.Z`: Granular releases (e.g., `v0.1.0` for early feature builds).

To retag an image:
```bash
podman tag power-bi-mcp:latest power-bi-mcp:v1.0.0
```

### 2. Updating Dependencies
When dependencies in `pyproject.toml` are modified:
1. Update lock file: `poetry update`
2. Rebuild the image: `podman build --no-cache -t power-bi-mcp:latest .`

### 3. Safely Replacing Running Services
If the MCP service is integrated into a workflow client (e.g. OpenWebUI):
1. Build and tag the new container version:
   ```bash
   podman build -t power-bi-mcp:v2 .
   ```
2. Stop the active detached container (if running):
   ```bash
   podman stop power-bi-mcp-bg
   ```
3. Update the client config (such as OpenWebUI configuration block) to point to the new version tag if necessary.

### 4. CI/CD Integration
* Configure pipelines to automatically run `poetry run python -m unittest` on code pushes.
* Trigger container builds on successful test runs, tagging them with the repository commit SHA before rolling them out to the user's host environment.
