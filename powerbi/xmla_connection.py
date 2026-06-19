import socket
import os
import json
import shutil
import subprocess
import uuid

class XMLAConnection:
    def __init__(self, port: int, host: str = "localhost"):
        self.port = port
        self.host = host
        self.endpoint = f"http://{host}:{port}/xmla"
        self.active_database = "db"  # Will be updated by discover_database
        self.has_powershell = shutil.which("powershell.exe") is not None

    def _run_powershell(self, script: str) -> str:
        # Enforce UTF-8 encoding for PowerShell output to handle non-ASCII/regional characters cleanly
        full_script = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n" + script
        temp_dir = "/mnt/c/Temp"
        os.makedirs(temp_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex
        script_name = f"mcp_xmla_query_{unique_id}.ps1"
        script_path = os.path.join(temp_dir, script_name)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_script)
            
        win_path = f"C:\\Temp\\{script_name}"
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", win_path]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding='utf-8', errors='replace', timeout=25)
            return proc.stdout
        except subprocess.TimeoutExpired:
            return ""
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass

    def _wrap_rows_in_soap_dict(self, rows):
        if isinstance(rows, dict) and "error" in rows:
            return rows
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "ExecuteResponse": {
                        "return": {
                            "results": {
                                "root": {
                                    "row": rows
                                }
                            }
                        }
                    }
                }
            }
        }

    def _extract_rows(self, xmla_result: dict) -> list[dict]:
        """Extracts row objects from typical SSAS XMLA ExecuteResponse dict."""
        try:
            if isinstance(xmla_result, dict) and "error" in xmla_result:
                return []
                
            envelope = xmla_result.get("soap:Envelope") or xmla_result.get("Envelope") or {}
            body = envelope.get("soap:Body") or envelope.get("Body") or {}
            execute_response = body.get("ExecuteResponse") or {}
            ret = execute_response.get("return") or {}
            results = ret.get("results") or {}
            root = results.get("root") or {}
            
            row_data = root.get("row")
            if not row_data:
                for key, val in root.items():
                    if key.endswith("row"):
                        row_data = val
                        break
            
            if not row_data:
                return []
                
            if isinstance(row_data, dict):
                return [row_data]
            return list(row_data)
        except Exception:
            return []

    async def discover_database(self):
        """Discovers the database catalog GUID name on the local SSAS instance."""
        query = "SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS"
        orig_database = self.active_database
        self.active_database = ""
        try:
            res = await self.execute_xmla(query)
            rows = self._extract_rows(res)
            if rows:
                self.active_database = rows[0].get("CATALOG_NAME", "db")
            else:
                self.active_database = orig_database
        except Exception:
            self.active_database = orig_database

    async def upsert_measure(self, table: str, name: str, dax: str) -> dict:
        """Creates or updates a measure in the specified table using native TOM."""
        if self.has_powershell:
            ps_script = f"""
$tableName = "{table}"
$measureName = "{name}"
$expression = @'
{dax}
'@

$p = Get-Process msmdsrv -ErrorAction SilentlyContinue
if ($p) {{
    $binPath = Split-Path -Path $p[0].Path -Parent
    $tomDll = Join-Path -Path $binPath -ChildPath "Microsoft.AnalysisServices.Server.Tabular.dll"
    if (Test-Path $tomDll) {{
        [System.Reflection.Assembly]::LoadFrom($tomDll) | Out-Null
        $server = New-Object Microsoft.AnalysisServices.Tabular.Server
        try {{
            $server.Connect("localhost:{self.port}")
            $database = $server.Databases[0]
            $tbl = $database.Model.Tables[$tableName]
            if ($tbl) {{
                $measure = $tbl.Measures[$measureName]
                if (-not $measure) {{
                    $measure = New-Object Microsoft.AnalysisServices.Tabular.Measure
                    $measure.Name = $measureName
                    $tbl.Measures.Add($measure) | Out-Null
                }}
                $measure.Expression = $expression
                $database.Model.SaveChanges() | Out-Null
                Write-Output '{{"status": "success"}}'
            }} else {{
                Write-Output '{{"status": "error", "message": "Table not found"}}'
            }}
        }} catch {{
            Write-Output (@{{status="error"; message=$_.ToString()}} | ConvertTo-Json)
        }} finally {{
            $server.Disconnect()
        }}
    }} else {{
        Write-Output '{{"status": "error", "message": "TOM DLL not found"}}'
    }}
}} else {{
    Write-Output '{{"status": "error", "message": "No msmdsrv process found"}}'
}}
"""
            out = self._run_powershell(ps_script)
            try:
                res = json.loads(out.strip())
            except Exception:
                res = {"status": "error", "message": out}
            return res
        else:
            raise RuntimeError("PowerShell is required to write measures to local PowerBI Desktop.")

    async def execute_xmla(self, payload: str) -> dict:
        """Sends a SOAP/XMLA payload or executes TMSL, returning parsed JSON dictionary."""
        is_tmsl = False
        try:
            stripped = payload.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                json.loads(stripped)
                is_tmsl = True
        except ValueError:
            pass

        if self.has_powershell:
            if is_tmsl:
                ps_script = f"""
$p = Get-Process msmdsrv -ErrorAction SilentlyContinue
if ($p) {{
    $binPath = Split-Path -Path $p[0].Path -Parent
    $tomDll = Join-Path -Path $binPath -ChildPath "Microsoft.AnalysisServices.Server.Tabular.dll"
    if (Test-Path $tomDll) {{
        [System.Reflection.Assembly]::LoadFrom($tomDll) | Out-Null
        $server = New-Object Microsoft.AnalysisServices.Tabular.Server
        try {{
            $server.Connect("localhost:{self.port}")
            $res = $server.Execute(@'
{payload}
'@)
            $output = @{{ status = "success"; messages = @() }}
            if ($res.Errors) {{
                $output.status = "error"
                foreach ($err in $res.Errors) {{
                    $output.messages += $err.Message
                }}
            }}
            Write-Output (ConvertTo-Json $output -Depth 4)
        }} catch {{
            Write-Output (@{{status="error"; message=$_.ToString()}} | ConvertTo-Json)
        }} finally {{
            $server.Disconnect()
        }}
    }} else {{
        Write-Output '{{"status": "error", "message": "TOM DLL not found"}}'
    }}
}} else {{
    Write-Output '{{"status": "error", "message": "No msmdsrv process found"}}'
}}
"""
                out = self._run_powershell(ps_script)
                try:
                    res = json.loads(out.strip())
                except Exception:
                    res = {"status": "error", "message": out}
                return self._wrap_rows_in_soap_dict(res)
            else:
                catalog_part = f"Initial Catalog={self.active_database};" if self.active_database else ""
                ps_script = f"""
$connStr = "Provider=MSOLAP;Data Source=localhost:{self.port};{catalog_part}"
$conn = New-Object System.Data.OleDb.OleDbConnection($connStr)
try {{
    $conn.Open()
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = @'
{payload}
'@
    $reader = $cmd.ExecuteReader()
    $rows = @()
    while ($reader.Read()) {{
        $row = @{{}}
        for ($i = 0; $i -lt $reader.FieldCount; $i++) {{
            $name = $reader.GetName($i)
            $val = $reader.GetValue($i)
            if ($val -eq [DBNull]::Value) {{
                $row[$name] = $null
            }} else {{
                $row[$name] = $val
            }}
        }}
        $rows += $row
    }}
    Write-Output (ConvertTo-Json $rows -Depth 4)
}} catch {{
    Write-Output (@{{error=$_.ToString()}} | ConvertTo-Json)
}} finally {{
    $conn.Close()
}}
"""
                out = self._run_powershell(ps_script)
                try:
                    rows = json.loads(out.strip())
                except Exception as e:
                    rows = {"error": f"Failed to parse PowerShell output: {out}. Error: {e}"}
                return self._wrap_rows_in_soap_dict(rows)
        else:
            raise RuntimeError(
                "PowerShell (powershell.exe) is required to run commands. "
                "Local Power BI Desktop Analysis Services instances speak MS-OLAP over binary TCP only, "
                "and do not host XMLA-over-HTTP SOAP endpoints."
            )
