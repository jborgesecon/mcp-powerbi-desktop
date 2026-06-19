$connStr = "Provider=MSOLAP;Data Source=localhost:62903;Initial Catalog=27884d8c-f4b6-4439-bd14-68b6a65f8fd3;"
$conn = New-Object System.Data.OleDb.OleDbConnection($connStr)
try {
    $conn.Open()
    $cmd = $conn.CreateCommand()
    
    $xmla = '
    <Alter ObjectExpansion="ObjectProperties" xmlns="http://schemas.microsoft.com/analysisservices/2003/engine">
      <Object>
        <DatabaseID>27884d8c-f4b6-4439-bd14-68b6a65f8fd3</DatabaseID>
        <TableID>Tabela</TableID>
        <MeasureID>TestMeasure</MeasureID>
      </Object>
      <ObjectDefinition>
        <Measure>
          <ID>TestMeasure</ID>
          <Name>TestMeasure</Name>
          <Expression>1 + 1</Expression>
        </Measure>
      </ObjectDefinition>
    </Alter>'
    
    $cmd.CommandText = $xmla
    $res = $cmd.ExecuteNonQuery()
    Write-Output "Success! Result: $res"
} catch {
    Write-Output "Error: $_"
} finally {
    $conn.Close()
}
