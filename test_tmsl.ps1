$connStr = "Provider=MSOLAP;Data Source=localhost:62903;Initial Catalog=27884d8c-f4b6-4439-bd14-68b6a65f8fd3;"
$conn = New-Object System.Data.OleDb.OleDbConnection($connStr)
try {
    $conn.Open()
    $cmd = $conn.CreateCommand()
    
    $tmsl = '{
        "alter": {
            "object": {
                "database": "27884d8c-f4b6-4439-bd14-68b6a65f8fd3",
                "table": "Tabela",
                "measure": "TestMeasure"
            },
            "measure": {
                "name": "TestMeasure",
                "expression": "1 + 1"
            }
        }
    }'
    
    $cmd.CommandText = $tmsl
    $res = $cmd.ExecuteNonQuery()
    Write-Output "Success! Result: $res"
} catch {
    Write-Output "Error: $_"
} finally {
    $conn.Close()
}
