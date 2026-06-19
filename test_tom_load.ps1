$p = Get-Process msmdsrv -ErrorAction SilentlyContinue
if ($p) {
    $binPath = Split-Path -Path $p[0].Path -Parent
    $tomDll = Join-Path -Path $binPath -ChildPath "Microsoft.AnalysisServices.Server.Tabular.dll"
    if (Test-Path $tomDll) {
        try {
            [System.Reflection.Assembly]::LoadFrom($tomDll) | Out-Null
            # Check if Tabular Server class exists in loaded assemblies
            $types = [AppDomain]::CurrentDomain.GetAssemblies() | 
                     Where-Object { $_.FullName -match "AnalysisServices" } | 
                     ForEach-Object { $_.GetTypes() } | 
                     Where-Object { $_.FullName -match "Tabular.Server" }
            if ($types) {
                Write-Output "Found Tabular Server class in $tomDll!"
            } else {
                Write-Output "Loaded $tomDll, but Tabular Server class not found."
            }
        } catch {
            Write-Output "Error: $_"
        }
    } else {
        Write-Output "DLL not found at $tomDll!"
    }
} else {
    Write-Output "No msmdsrv process found!"
}
