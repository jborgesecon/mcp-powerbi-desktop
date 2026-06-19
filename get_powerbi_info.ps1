$processes = Get-Process msmdsrv -ErrorAction SilentlyContinue
if (-not $processes) {
    Write-Output '{"instances_count": 0, "instances": []}'
    exit
}

$results = @()

foreach ($p in $processes) {
    $procId = $p.Id
    # Find listening port from netstat
    $netstat = netstat.exe -ano | Select-String "LISTENING" | Select-String "\b$procId\b"
    $port = $null
    foreach ($line in $netstat) {
        if ($line.Line -match '127\.0\.0\.1:(\d+)') {
            $port = [int]$Matches[1]
            break
        }
    }
    
    if (-not $port) {
        continue
    }
    
    # Query XMLA for catalogs
    $url = "http://127.0.0.1:$port/xmla"
    $soapCatalog = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Execute xmlns="urn:schemas-microsoft-com:xml-analysis"><Command><Statement>SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS</Statement></Command><Properties><PropertyList><Format>Tabular</Format></PropertyList></Properties></Execute></soap:Body></soap:Envelope>'
    $headers = @{ "SOAPAction" = '"urn:schemas-microsoft-com:xml-analysis:Execute"' }
    
    $catalog = "db"
    $catalog_error = $null
    try {
        $resCatalog = Invoke-RestMethod -Uri $url -Method Post -Body $soapCatalog -ContentType "text/xml; charset=utf-8" -Headers $headers -TimeoutSec 5
        $row = $resCatalog.Envelope.Body.ExecuteResponse.return.results.root.row
        if ($row) {
            $catalog = $row.CATALOG_NAME
        }
    } catch {
        $catalog_error = $_.ToString()
    }
    
    # Query XMLA for dimensions/tables using the discovered catalog
    $catalog_element = "<Catalog>$catalog</Catalog>"
    $soapTables = @"
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Execute xmlns="urn:schemas-microsoft-com:xml-analysis">
      <Command>
        <Statement>SELECT [Dimension_Unique_Name] FROM `$SYSTEM.MDSCHEMA_DIMENSIONS WHERE [Dimension_Is_Shared] = True</Statement>
      </Command>
      <Properties>
        <PropertyList>
          $catalog_element
          <Format>Tabular</Format>
        </PropertyList>
      </Properties>
    </Execute>
  </soap:Body>
</soap:Envelope>
"@

    $tables = @()
    $tables_error = $null
    try {
        $resTables = Invoke-RestMethod -Uri $url -Method Post -Body $soapTables -ContentType "text/xml; charset=utf-8" -Headers $headers -TimeoutSec 5
        $rows = $resTables.Envelope.Body.ExecuteResponse.return.results.root.row
        if ($rows) {
            $rowsArray = @($rows)
            foreach ($r in $rowsArray) {
                $uniqueName = $r.Dimension_Unique_Name
                if ($uniqueName) {
                    $cleanName = $uniqueName.Trim("[]")
                    if ($cleanName -and $tables -notcontains $cleanName) {
                        $tables += $cleanName
                    }
                }
            }
        }
    } catch {
        $tables_error = $_.ToString()
    }
    
    $results += [PSCustomObject]@{
        pid = $procId
        port = $port
        catalog = $catalog
        catalog_error = $catalog_error
        tables_count = $tables.Count
        tables = $tables
        tables_error = $tables_error
    }
}

$output = @{
    instances_count = $results.Count
    instances = $results
}

Write-Output (ConvertTo-Json $output -Depth 4)
