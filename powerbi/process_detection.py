import os
import re
import psutil
import shutil
import subprocess
import json
import uuid

def detect_instances() -> list[dict]:
    """
    Returns a list of detected local Power BI SSAS instances.
    Each instance is represented by a dictionary containing the port and name.
    """
    # 1. Explicit configuration via Environment Variable (highest priority)
    env_port = os.environ.get("POWERBI_PORT")
    if env_port:
        try:
            return [{
                "port": int(env_port), 
                "name": "ExplicitEnvInstance", 
                "database_name": "db", 
                "table_count": 0, 
                "measure_count": 0
            }]
        except ValueError:
            pass

    # 2. Windows Host Process/Port detection via PowerShell (if available)
    if shutil.which("powershell.exe") is not None:
        ps_script = """
$processes = Get-Process msmdsrv -ErrorAction SilentlyContinue
$results = @()
if ($processes) {
    $binPath = Split-Path -Path $processes[0].Path -Parent
    $tomDll = Join-Path -Path $binPath -ChildPath "Microsoft.AnalysisServices.Server.Tabular.dll"
    $hasTom = $false
    if (Test-Path $tomDll) {
        try {
            [System.Reflection.Assembly]::LoadFrom($tomDll) | Out-Null
            $hasTom = $true
        } catch {}
    }
    
    foreach ($p in $processes) {
        $procId = $p.Id
        $netstat = netstat.exe -ano | Select-String "LISTENING" | Select-String "\\b$procId\\b"
        $port = $null
        foreach ($line in $netstat) {
            if ($line.Line -match '127\\.0\\.0\\.1:(\\d+)') {
                $port = [int]$Matches[1]
                break
            }
        }
        if ($port) {
            $dbName = "db"
            $tableCount = 0
            $measureCount = 0
            
            if ($hasTom) {
                try {
                    $server = New-Object Microsoft.AnalysisServices.Tabular.Server
                    $server.Connect("localhost:$port")
                    if ($server.Databases.Count -gt 0) {
                        $db = $server.Databases[0]
                        $dbName = $db.Name
                        foreach ($t in $db.Model.Tables) {
                            if ($t.Name -notmatch "^LocalDateTable_" -and $t.Name -notmatch "^DateTableTemplate_") {
                                $tableCount++
                                $measureCount += $t.Measures.Count
                            }
                        }
                    }
                    $server.Disconnect()
                } catch {}
            }
            
            $results += @{
                pid = $procId
                port = $port
                name = "PBIX_PID_$procId"
                database_name = $dbName
                table_count = $tableCount
                measure_count = $measureCount
            }
        }
    }
}
Write-Output (ConvertTo-Json $results -Depth 4)
"""
        temp_dir = "/mnt/c/Temp"
        os.makedirs(temp_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex
        script_name = f"mcp_instance_detect_{unique_id}.ps1"
        script_path = os.path.join(temp_dir, script_name)
        full_script = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n" + ps_script
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_script)
            
        win_path = f"C:\\Temp\\{script_name}"
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", win_path]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding='utf-8', errors='replace', timeout=20)
            out = proc.stdout.strip()
            if out:
                instances = json.loads(out)
                if isinstance(instances, dict):
                    return [instances]
                return list(instances)
        except Exception:
            pass
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass

    # 3. Scanning local Linux processes (fallback if not in WSL and no powershell.exe)
    instances = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == 'msmdsrv.exe':
                cmdline = proc.info['cmdline'] or []
                cmd_str = " ".join(cmdline)
                port_match = re.search(r'-s\s+(\d+)|localhost:(\d+)|-n\s+(\d+)', cmd_str)
                if port_match:
                    port = int(next(p for p in port_match.groups() if p is not None))
                    instances.append({
                        "pid": proc.info['pid'],
                        "port": port,
                        "name": f"PBIX_PID_{proc.info['pid']}",
                        "database_name": "db",
                        "table_count": 0,
                        "measure_count": 0
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return instances
