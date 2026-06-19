$p = Get-Process msmdsrv -ErrorAction SilentlyContinue
if ($p) {
    $binPath = Split-Path -Path $p[0].Path -Parent
    $tomDll = Join-Path -Path $binPath -ChildPath "Microsoft.AnalysisServices.Server.Tabular.dll"
    if (Test-Path $tomDll) {
        try {
            [System.Reflection.Assembly]::LoadFrom($tomDll) | Out-Null
            $server = New-Object Microsoft.AnalysisServices.Tabular.Server
            $server.Connect("localhost:62903")
            $database = $server.Databases[0]
            
            $table = $database.Model.Tables["Tabela"]
            if ($table) {
                $measureName = "TestMeasure"
                $measure = $table.Measures[$measureName]
                if (-not $measure) {
                    $measure = New-Object Microsoft.AnalysisServices.Tabular.Measure
                    $measure.Name = $measureName
                    $table.Measures.Add($measure)
                    Write-Output "Creating new measure $measureName..."
                } else {
                    Write-Output "Updating existing measure $measureName..."
                }
                $measure.Expression = "1 + 1"
                
                # Save changes
                $database.Model.SaveChanges()
                Write-Output "Success! Measure created/updated."
            } else {
                Write-Output "Table 'Tabela' not found in model."
            }
            $server.Disconnect()
        } catch {
            Write-Output "Error: $_"
        }
    } else {
        Write-Output "DLL not found at $tomDll"
    }
} else {
    Write-Output "No msmdsrv process found"
}
