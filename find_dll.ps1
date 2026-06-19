$path = "C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_2.155.756.0_x64__8wekyb3d8bbwe"
Get-ChildItem -Path $path -Filter "*AnalysisServices*.dll" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
