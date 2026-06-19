$listenPort = 54049
$connectPort = 62903
$connectAddress = "127.0.0.1"

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $listenPort)
$listener.Start()

Write-Host "Proxy listening on 0.0.0.0:$listenPort -> $connectAddress:$connectPort"

try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        $remote = [System.Net.Sockets.TcpClient]::new($connectAddress, $connectPort)
        
        $clientStream = $client.GetStream()
        $remoteStream = $remote.GetStream()
        
        $task1 = [System.Threading.Tasks.Task]::Run({
            try {
                $buf = New-Object byte[] 65536
                while ($true) {
                    $read = $clientStream.Read($buf, 0, 65536)
                    if ($read -eq 0) { break }
                    $remoteStream.Write($buf, 0, $read)
                }
            } catch {
                # Connection reset/closed
            } finally {
                $client.Close()
                $remote.Close()
            }
        })
        
        $task2 = [System.Threading.Tasks.Task]::Run({
            try {
                $buf = New-Object byte[] 65536
                while ($true) {
                    $read = $remoteStream.Read($buf, 0, 65536)
                    if ($read -eq 0) { break }
                    $clientStream.Write($buf, 0, $read)
                }
            } catch {
                # Connection reset/closed
            } finally {
                $client.Close()
                $remote.Close()
            }
        })
    }
} finally {
    $listener.Stop()
}
