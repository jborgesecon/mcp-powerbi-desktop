# Power BI Desktop Companion MCP Server

A Model Context Protocol (MCP) server that acts as a local companion tool for actively running Power BI Desktop (`.pbix`) sessions. It attaches to the live in-memory Analysis Services engine on the local machine (similar to DAX Studio or Tabular Editor).

This companion tool is designed ONLY for local running Power BI Desktop instances. It communicates using Windows PowerShell interop to run OLE DB queries and Tabular Object Model (TOM) mutations.

---

## Architecture & Features

1. **Windows PowerShell OLE DB / TOM Bridge**: Executes native OLE DB commands (using the MSOLAP provider) and Tabular Object Model (TOM) scripts directly against the host machine's Analysis Services engine.
2. **Dynamic Host Instance Discovery**: Scans host processes to locate the dynamic ports, PIDs, database catalog GUIDs, table counts, and measure counts of all open `.pbix` files.
3. **Case-Insensitive Metadata Parsing**: Robust schema extraction from system DMVs, filtering out internal tables (`LocalDateTable_*`, `DateTableTemplate_*`) to present clean models.
4. **Live Model Mutations**: Directly creates or updates measures in the active `.pbix` session in-memory, committing changes using TOM's `SaveChanges()`.
5. **Stateful Connection Management**: Retains connection info (selected port and database catalog) in-memory across MCP requests, auto-selecting if only one instance is active.

---

## Tools Exposed

- `list_instances`: Lists active local Power BI Desktop instances and their ports.
- `select_instance(port)`: Connects the MCP server session to a specific port.
- `get_model_metadata`: Returns a token-efficient summary of tables and measures.
- `list_measures`: Returns all measure names, expressions, and parent tables.
- `get_measure(name)`: Retrieves the DAX formula for a specific measure.
- `create_measure(table, name, dax)`: Creates a new measure in a table.
- `update_measure(table, name, dax)`: Updates an existing measure's formula.
- `create_or_update_measure(table, name, dax)`: Unified tool to create or update a measure.
- `run_tmsl(script)`: Runs Tabular Model Scripting Language (TMSL) scripts.

---

## Prerequisites & Installation

### Requirements
- Python 3.11+
- Power BI Desktop running on Windows
- Execution environment: Directly on Windows, or via WSL2 (with PowerShell interop enabled).

### Installation
```bash
cd power-bi
pip install -e .
```

### Running the MCP Server
Run the python server directly to enable standard I/O communication:
```bash
python3 mcp_server.py
```
